from dataclasses import dataclass

@dataclass
class Account:
    """A dataclass to hold all information for a single miner account."""
    name: str
    address: str
    private_key: str
    api_port: int

    @property
    def api_url(self) -> str:
        return f"http://localhost:{self.api_port}"

# The Single Source of Truth for all miner account information.
ACCOUNTS = {
    "miner1": Account(
        name="miner1",
        address="STB44HYPYAT2BB2QE513NSP81HTMYWBJP02HPGK6", 
        private_key="cb3df38053d132895220b9ce471f6b676db5b9bf0b4adefb55f2118ece2478df01",
        api_port=20443
    ),
    "miner2": Account(
        name="miner2",
        address="ST11NJTTKGVT6D1HY4NJRVQWMQM7TVAR091EJ8P2Y", 
        private_key="21d43d2ae0da1d9d04cfcaac7d397a33733881081f0b2cd038062cf0ccbb752601",
        api_port=30443
    ),
    "miner3": Account(
        name="miner3",
        address="ST3AM1A56AK2C1XAFJ4115ZSV26EB49BVQ10MGCS0", 
        private_key="7036b29cb5e235e5fd9b09ae3e8eec4404e44906814d5d01cbca968a60ed4bfb01",
        api_port=40443
    )
}

