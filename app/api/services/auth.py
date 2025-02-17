from fastapi import HTTPException, status

from app.api.services.permission import PermissionService
from app.client.web3 import Web3Client
from app.db.models import App, Auth, User
from app.schema.dependencies import AuthState
from app.utils.enums import ClientTypeEnum, PermissionEnum


class AuthService:

    async def generate_auth(self, auth_obj: AuthState, client_type: ClientTypeEnum):
        # only callable via FIRST_PARTY app, we know to reference the user obj.
        search_criteria = {}
        if client_type == ClientTypeEnum.APP:
            app = await App.get(owner_id=auth_obj.app_id)
            search_criteria["app_id"] = app.id
        else:
            user = await User.get(id=auth_obj.user_id)
            search_criteria["user_id"] = user.id

        auth = await Auth.filter(**search_criteria).first()
        api_key, hash_key = Auth.create_credentials()
        if auth:
            # regenerate
            auth.hashed_key = hash_key
            await auth.save()
            return api_key

        # evaluate permissions, then create
        permission_service = PermissionService()

        identifier = user.id if client_type == ClientTypeEnum.USER else app.id
        has_permission = await permission_service.has_permission(
            client_type=client_type,
            identifier=identifier,
            permission=PermissionEnum.CREATE_API_KEY,
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="incorrect permissions"
            )

        await Auth.create(
            **search_criteria, client_type=client_type, hashed_key=hash_key
        )

        return api_key

    async def revoke_access(self):
        pass

    async def sync_credits(self, auth: AuthState):
        web3_client = Web3Client()
        provider = web3_client.get_deployed_provider()

        user = await User.get(id=auth.user_id)

        prev_credits = user.total_credits

        # Get the contract instance
        contract_address = "0xe7f1725e7734ce288f8367e1bb143e90bb3f0512".lower()
        abi = [
            {
                "inputs": [{"type": "address"}],
                "name": "apiCredits",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            }
        ]
        contract_address_use = provider.to_checksum_address(contract_address)
        contract = provider.eth.contract(address=contract_address_use, abi=abi)

        # Call apiCredits mapping to get credits for the address
        address_use = provider.to_checksum_address(user.address.lower())
        credits_raw = await contract.functions.apiCredits(address_use).call()
        credits = credits_raw / 10**18

        # the contract is the source of truth. Always overwrite.
        user.total_credits = credits
        await user.save()

        return {
            "total_credits": credits,
            "credits_added": max(0, credits - prev_credits),
            "credits_removed": max(
                0, prev_credits - credits
            ),  # only applicable during refund.
        }
