from .services import publication_payload, active_release


def validate_before_publish():
    return publication_payload()


def validate_active_manifest():
    return active_release()
