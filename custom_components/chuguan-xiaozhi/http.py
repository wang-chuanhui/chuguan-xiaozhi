from homeassistant.components.api import APIConfigView

class CGAPIConfigView(APIConfigView):
    """Chuguan API Config View."""
    name = "api:cgconfig"
    url = "/api/cgconfig"
    requires_auth = False