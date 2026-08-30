from moriyama_mail.config import Settings
from moriyama_mail.myasp.gateway import MyAspGateway
from moriyama_mail.myasp.mock import MockMyAspGateway


def build_myasp_gateway(settings: Settings) -> MyAspGateway:
    if settings.myasp_live:
        from moriyama_mail.myasp.browser import BrowserMyAspGateway

        return BrowserMyAspGateway(settings)
    return MockMyAspGateway()
