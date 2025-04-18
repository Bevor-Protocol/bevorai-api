import json
from typing import AsyncGenerator, Optional

import numpy as np
import tiktoken
from numpy.typing import NDArray
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_core import to_json
from tortoise.query_utils import Prefetch

from app.db.models import Chat, ChatMessage
from app.lib.clients.llm import chat_agent, llm_client
from app.utils.types.enums import ChatRoleEnum
from app.utils.types.shared import AuthState


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

    async def _get_top_k_indices(
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

    def _prepare_context(
        self, embedding: list[float], chat: Chat
    ) -> list[ModelMessage]:
        """
        Generate context as message_history, manipulating the context provided to each chat.
        """

        chat_messages: list[ChatMessage] = chat.messages_sorted

        if not chat_messages:
            return []

        messages = list(
            map(
                lambda x: ModelMessagesTypeAdapter.validate_json(x.message)[0],
                chat_messages,
            )
        )
        embeddings = list(map(lambda x: x.embedding, chat_messages))

        similar_indices = self._get_top_k_indices(
            cur_embedding=embedding, existing_embeddings=embeddings
        )
        similar_messages_dedup = [
            messages[i] for i in similar_indices if i > self.recency_k
        ]

        context_messages = [
            ModelRequest(parts=[SystemPromptPart(content=chat.audit.contract.code)]),
            ModelRequest(parts=[SystemPromptPart(content=chat.audit.raw_output)]),
        ]
        context_messages.append(
            ModelRequest(
                parts=[SystemPromptPart(content="these are the most recent messages:")]
            )
        )

        context_messages.extend(messages[: self.recency_k])
        if similar_messages_dedup:
            context_messages.append(
                ModelRequest(
                    parts=[
                        SystemPromptPart(
                            content="and these are the most relevant past messages:"
                        )
                    ]
                )
            )
            context_messages.extend(similar_messages_dedup)

        return context_messages

    def _to_chat_message(m: ModelMessage) -> ChatMessage:
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
                    "role": "model",
                    "timestamp": m.timestamp.isoformat(),
                    "content": first_part.content,
                }

        raise UnexpectedModelBehavior(f"Unexpected message type for chat app: {m}")

    def _get_token_count(self, text: str, model: Optional[str] = None) -> int:
        encoding = tiktoken.encoding_for_model(model or self.embedding_model)
        return len(encoding.encode(text))

    async def chat(
        self, auth: AuthState, chat_id: str, message: str
    ) -> AsyncGenerator[bytes, None]:
        message_queryset = ChatMessage.all().order_by("-created_at")
        message_pf = Prefetch(queryset=message_queryset, to_attr="messages_sorted")

        existing_chat = (
            await Chat.get(id=chat_id, user_id=auth.user_id)
            .select_related("audit__contract")
            .prefetch_related(message_pf)
        )

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
            n_tokens=self._get_token_count(message),
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
