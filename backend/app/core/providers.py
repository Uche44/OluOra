"""Provider identifiers shared across identity and data integrations."""

GOOGLE = "google"
YOUTUBE = "youtube"
TIKTOK = "tiktok"

# Providers that can be connected as a data source (one SocialAccount row each).
DATA_PROVIDERS = (YOUTUBE, TIKTOK)

# OAuth state `flow` values.
FLOW_LOGIN = "login"
FLOW_YOUTUBE_CONNECT = "youtube_connect"
FLOW_TIKTOK_CONNECT = "tiktok_connect"

FLOW_TO_PROVIDER = {
    FLOW_YOUTUBE_CONNECT: YOUTUBE,
    FLOW_TIKTOK_CONNECT: TIKTOK,
}
