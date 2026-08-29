from moriyama_mail.config import Settings
from moriyama_mail.myasp.gateway import MyAspGateway
from moriyama_mail.myasp.mock import MockMyAspGateway


def build_myasp_gateway(settings: Settings) -> MyAspGateway:
    # Live implementation is intentionally not wired in Phase 1.
    _ = settings
    return MockMyAspGateway()
