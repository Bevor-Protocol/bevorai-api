import json
from ast import literal_eval
from typing import AsyncGenerator

import numpy as np

# import tiktoken
from numpy.typing import NDArray
from pydantic import ConfigDict, TypeAdapter
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_core import to_json
from tortoise.query_utils import Prefetch

from app.api.chat.interface import ChatMessageDict
from app.db.models import Audit, Chat, ChatMessage
from app.lib.clients.llm import chat_agent, llm_client
from app.utils.types.enums import ChatRoleEnum, FindingLevelEnum
from app.utils.types.shared import AuthState

ModelMessageAdapter = TypeAdapter(
    ModelMessage, config=ConfigDict(defer_build=True, ser_json_bytes="base64")
)


class ChatService:
    embedding_model = "text-embedding-3-small"
    top_k = 2
    recency_k = 4

    """
    It seems tortoise ORM has no support for pgvector. We'll use JSONB field,
    and rely on in-memory numpy to do search. I intentionally shrink the embedding
    dimension to decrease compute cost.
    """

    async def initiate_chat(self, auth: AuthState, audit_id: str):
        chat = await Chat.create(user_id=auth.user_id, audit_id=audit_id)

        return chat

    async def _create_embedding(self, content: str) -> list[float]:
        embedding = await llm_client.embeddings.create(
            input=content,
            model=self.embedding_model,
            dimensions=100,  # default is 1536, but we can override this without losing too much signal
        )

        return embedding.data[0].embedding

    def cosine_similarity(
        self, current_embedding: list[float], existing_embeddings: list[float]
    ) -> NDArray[np.float64]:
        """
        a: 1D array-like vector -> represents embedding of current message
        B: 2D array-like of shape (n_vectors, vector_dim) -> existing embeddings to compare against.
        Returns: 1D array of cosine similarities
        """

        a = np.array(current_embedding)
        B = np.array(existing_embeddings)

        # Normalize a and B
        a_norm = a / np.linalg.norm(a)
        B_norm = B / np.linalg.norm(B, axis=1, keepdims=True)

        # Compute dot product between a and each row in B
        similarities = np.dot(B_norm, a_norm)

        return similarities  # shape: (n_vectors,)

    def _get_top_k_indices(
        self, cur_embedding: list[float], existing_embeddings: list[list[float]]
    ) -> list[int]:
        """
        We'll take an approach of recency bias plus context awareness.
        Meaning always inject past recency_k messages, and inject top_k messages,
        as long as they don't overlap with the recency_k.

        This should provide a solid context while retaining potentially old yet relevent messages
        """

        similarities = self.cosine_similarity(cur_embedding, existing_embeddings)

        top_k_indices = np.argsort(similarities)[-self.top_k :][::-1]

        return top_k_indices

    async def _prepare_context(
        self, embedding: list[float], chat: Chat
    ) -> list[ModelMessage]:
        """
        Generate context as message_history, manipulating the context provided to each chat.
        """

        chat_messages: list[ChatMessage] = chat.messages_sorted

        audit = (
            await Audit.get(id=chat.audit_id)
            .select_related("contract")
            .prefetch_related("findings")
        )

        audit_findings_prompt = ""
        audit_findings_prompt += f"Introduction:\n{audit.introduction}"
        audit_findings_prompt += f"\nScope:\n{audit.scope}"
        findings = {}
        for finding in audit.findings:
            if finding.level not in findings:
                findings[finding.level] = []
            findings[finding.level].append(
                f"Explanation: {finding.explanation}\nRecommendation: {finding.recommendation}\nReference: {finding.reference}"
            )

        for level in [
            FindingLevelEnum.CRITICAL,
            FindingLevelEnum.HIGH,
            FindingLevelEnum.MEDIUM,
            FindingLevelEnum.LOW,
        ]:
            if level.value not in findings:
                audit_findings_prompt += f"No {level} severity vulnerabilities"
                continue
            audit_findings_prompt += f"{level} severity vulnerabilities:"
            for f in findings[level]:
                audit_findings_prompt += f"\n{f}"

        audit_findings_prompt += f"\nConclusion:\n{audit.conclusion}"

        context_messages = [
            ModelRequest(
                parts=[
                    SystemPromptPart(
                        content=f"Code that was audited:\n {audit.contract.code}"
                    )
                ]
            ),
            ModelRequest(
                parts=[
                    SystemPromptPart(
                        content=f"Audit findings:\n{audit_findings_prompt}"
                    )
                ]
            ),
        ]

        if not chat_messages:
            return context_messages

        messages: list[ModelMessage] = list(
            map(
                lambda x: ModelMessageAdapter.validate_json(literal_eval(x.message)),
                chat_messages,
            )
        )
        embeddings = list(map(lambda x: x.embedding, chat_messages))

        similar_indices = self._get_top_k_indices(
            cur_embedding=embedding, existing_embeddings=embeddings
        )

        similar_messages_dedup = [
            messages[i] for i in similar_indices if (len(messages) - i) > self.recency_k
        ]

        # I was having issues with ordering in pydanticAI
        if similar_messages_dedup:
            relevant_context = "These are the most relevant past messages:"
            for m in similar_messages_dedup:
                writer = "Assistant" if m.kind == "response" else "User"
                relevant_context += f"\n{writer}: {m.parts[0].content}"
            context_messages.append(
                ModelRequest(parts=[SystemPromptPart(content=relevant_context)])
            )
        historical_context = "These are the most recent messages:"
        for m in messages[-self.recency_k :]:
            writer = "Assistant" if m.kind == "response" else "User"
            historical_context += f"\n{writer}: {m.parts[0].content}"
        context_messages.append(
            ModelRequest(parts=[SystemPromptPart(content=historical_context)])
        )

        return context_messages

    def _to_chat_message(self, m: ModelMessage) -> dict:
        first_part = m.parts[0]
        if isinstance(m, ModelRequest):
            if isinstance(first_part, UserPromptPart):
                assert isinstance(first_part.content, str)
                return {
                    "role": "user",
                    "timestamp": first_part.timestamp.isoformat(),
                    "content": first_part.content,
                }
        elif isinstance(m, ModelResponse):
            if isinstance(first_part, TextPart):
                return {
                    "role": "system",
                    "timestamp": m.timestamp.isoformat(),
                    "content": first_part.content,
                }

        raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")

    # def _get_token_count(self, text: str, model: Optional[str] = None) -> int:
    #     encoding = tiktoken.encoding_for_model(model or self.embedding_model)
    #     return len(encoding.encode(text))

    async def chat(
        self, auth: AuthState, chat_id: str, message: str
    ) -> AsyncGenerator[bytes, None]:
        message_queryset = ChatMessage.all().order_by("created_at")
        message_pf = Prefetch(
            relation="messages", queryset=message_queryset, to_attr="messages_sorted"
        )

        existing_chat = await Chat.get(
            id=chat_id, user_id=auth.user_id
        ).prefetch_related(message_pf)

        cur_embedding = await self._create_embedding(message)

        encoded_message = ModelRequest(
            parts=[
                UserPromptPart(
                    content=message,
                )
            ]
        )

        await ChatMessage.create(
            chat_id=chat_id,
            chat_role=ChatRoleEnum.USER,
            message=to_json(encoded_message),
            # n_tokens=self._get_token_count(message),
            n_tokens=0,
            model_name=self.embedding_model,
            embedding=cur_embedding,
        )

        model_context = await self._prepare_context(
            embedding=cur_embedding, chat=existing_chat
        )

        async with chat_agent.run_stream(
            message, message_history=model_context
        ) as result:
            async for text in result.stream(debounce_by=0.01):
                # text here is a `str` and the frontend wants
                # JSON encoded ModelResponse, so we create one
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(self._to_chat_message(m)).encode("utf-8") + b"\n"

        # add new messages (e.g. the user prompt and the agent response in this case) to the database
        newest_message = result.new_messages()[-1]
        response_embedding = await self._create_embedding(await result.get_data())

        await ChatMessage.create(
            chat_id=chat_id,
            chat_role=ChatRoleEnum.SYSTEM,
            message=to_json(newest_message),
            n_tokens=result.usage().response_tokens,
            model_name=self.embedding_model,
            embedding=response_embedding,
        )
        existing_chat.total_messages += 2
        await existing_chat.save()

    async def get_chats(self, auth: AuthState) -> list[Chat]:
        chats = await Chat.filter(user_id=auth.user_id, is_visible=True).select_related(
            "audit__contract"
        )

        return chats

    async def get_chat_messages(
        self, auth: AuthState, chat_id: str
    ) -> list[ChatMessageDict]:
        message_queryset = ChatMessage.all().order_by("created_at")
        message_pf = Prefetch(
            relation="messages", queryset=message_queryset, to_attr="messages_sorted"
        )

        existing_chat = await Chat.get(
            id=chat_id, user_id=auth.user_id
        ).prefetch_related(message_pf)

        messages: list[ChatMessage] = existing_chat.messages_sorted

        messages_structured = []
        for m in messages:
            structured = self._to_chat_message(
                ModelMessageAdapter.validate_json(
                    # x.message[1:] if x.message.startswith("b'") else x.message
                    literal_eval(m.message)
                )
            )
            messages_structured.append({"id": str(m.id), **structured})

        return messages_structured
