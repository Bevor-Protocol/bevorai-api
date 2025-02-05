import os

from .enums import NetworkEnum, NetworkTypeEnum

network_explorer_mapper = {
    NetworkEnum.BASE: "api.basescan.org",
    NetworkEnum.BASE_SEPOLIA: "api-sepolia.basescan.org",
    NetworkEnum.BSC: "api.bscscan.com",
    NetworkEnum.BSC_TEST: "api-testnet.bscscan.com",
    NetworkEnum.ETH: "api.etherscan.io",
    NetworkEnum.ETH_SEPOLIA: "api-sepolia.etherscan.io",
    NetworkEnum.POLYGON: "api.polygonscan.com",
    NetworkEnum.POLYGON_AMOY: "api-amoy.polygonscan.com",
    NetworkEnum.ARB: "api.arbiscan.io",  # Added ARB
    NetworkEnum.ARB_SEPOLIA: "api-sepolia.arbiscan.io",
    NetworkEnum.AVAX: "api.routescan.io",
    NetworkEnum.AVAX_FUJI: "api.routescan.io",
    NetworkEnum.MODE: "api.routescan.io",
    NetworkEnum.MODE_TESTNET: "api.routescan.io",
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
    NetworkEnum.ARB: os.getenv("ARBSCAN_API_KEY"),  # Added ARB
    NetworkEnum.ARB_SEPOLIA: os.getenv("ARBSCAN_API_KEY"),  # Added ARB testnet
    NetworkEnum.AVAX: os.getenv("SNOWTRACE_API_KEY"),  # Added AVAX
    NetworkEnum.AVAX_FUJI: os.getenv("SNOWTRACE_API_KEY"),  # Added AVAX testnet
    NetworkEnum.MODE: os.getenv("MODESCAN_API_KEY"),  # Added MODE
    NetworkEnum.MODE_TESTNET: os.getenv("MODESCAN_API_KEY"),  # Added MODE testnet
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
    NetworkEnum.AVAX: "avax-mainnet.g.alchemy.com",  # Added AVAX
    NetworkEnum.AVAX_FUJI: "avax-testnet.g.alchemy.com",  # Added AVAX testnet
    NetworkEnum.MODE: "mode-mainnet.g.alchemy.com",  # Added MODE
    NetworkEnum.MODE_TESTNET: "mode-testnet.g.alchemy.com",  # Added MODE testnet
    NetworkEnum.ARB: "arb-mainnet.g.alchemy.com",  # Added ARB
    NetworkEnum.ARB_SEPOLIA: "arb-sepolia.g.alchemy.com",  # Added ARB testnet
}

networks_by_type = {
    NetworkTypeEnum.MAINNET: [
        NetworkEnum.BASE,
        NetworkEnum.BSC,
        NetworkEnum.ETH,
        NetworkEnum.POLYGON,
        NetworkEnum.AVAX,  # Added AVAX
        NetworkEnum.MODE,  # Added MODE
        NetworkEnum.ARB,  # Added ARB
    ],
    NetworkTypeEnum.TESTNET: [
        NetworkEnum.BASE_SEPOLIA,
        NetworkEnum.BSC_TEST,
        NetworkEnum.ETH_SEPOLIA,
        NetworkEnum.POLYGON_AMOY,
        NetworkEnum.AVAX_FUJI,  # Added AVAX
        NetworkEnum.MODE_TESTNET,  # Added MODE
        NetworkEnum.ARB_SEPOLIA,  # Added ARB
    ],
}
