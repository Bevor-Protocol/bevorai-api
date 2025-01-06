import os

from .enums import NetworkEnum, NetworkTypeEnum

network_explorer_mapper = {
    NetworkEnum.BASE: "api.basescan.org",
    NetworkEnum.BASE_SEPOLIA: "api.api-sepolia.basescan.org",
    NetworkEnum.BSC: "api.bscscan.com",
    NetworkEnum.BSC_TEST: "api.api-testnet.bscscan.com",
    NetworkEnum.ETH: "api.etherscan.io",
    NetworkEnum.ETH_SEPOLIA: "api.api-sepolia.etherscan.io",
    NetworkEnum.POLYGON: "api.polygonscan.com",
    NetworkEnum.POLYGON_AMOY: "api.api-amoy.polygonscan.com",
}

network_explorer_apikey_mapper = {
    NetworkEnum.BASE: os.getenv("BASESCAN_API_KEY"),
    NetworkEnum.BASE_SEPOLIA: os.getenv("BASESCAN_API_KEY"),
    NetworkEnum.BSC: os.getenv("BSCSCAN_API_KEY"),
    NetworkEnum.BSC_TEST: os.getenv("BSCSCAN_API_KEY"),
    NetworkEnum.ETH: os.getenv("ETHERSCAN_API_KEY"),
    NetworkEnum.ETH_SEPOLIA: os.getenv("ETHERSCAN_API_KEY"),
    NetworkEnum.POLYGON: os.getenv("POLYGONSCAN_API_KEY"),
    NetworkEnum.POLYGON_AMOY: os.getenv("POLYGONSCAN_API_KEY"),
}

network_rpc_mapper = {
    NetworkEnum.BASE: "base-mainnet.g.alchemy.com",
    NetworkEnum.BASE_SEPOLIA: "base-sepolia.g.alchemy.com",
    NetworkEnum.BSC: "bnb-mainnet.g.alchemy.com",
    NetworkEnum.BSC_TEST: "bnb-testnet.g.alchemy.com",
    NetworkEnum.ETH: "eth-mainnet.g.alchemy.com",
    NetworkEnum.ETH_SEPOLIA: "eth-sepolia.g.alchemy.com",
    NetworkEnum.POLYGON: "polygon-mainnet.g.alchemy.com",
    NetworkEnum.POLYGON_AMOY: "polygon-amoy.g.alchemy.com",
}

networks_by_type = {
    NetworkTypeEnum.MAINNET: [
        NetworkEnum.BASE,
        NetworkEnum.BSC,
        NetworkEnum.ETH,
        NetworkEnum.POLYGON,
    ],
    NetworkTypeEnum.TESTNET: [
        NetworkEnum.BASE_SEPOLIA,
        NetworkEnum.BSC_TEST,
        NetworkEnum.ETH_SEPOLIA,
        NetworkEnum.POLYGON_AMOY,
    ],
}
