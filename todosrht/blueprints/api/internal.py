import gzip
import tarfile
from flask import Blueprint, abort, send_file
from srht.oauth import oauth

internal = Blueprint("api.internal", __name__)

@internal.route("/api/_internal/data-export")
@oauth(None, require_internal=True)
def data_export():
    return send_file("/home/sircmpwn/sources/libressl-2.5.1.tar.gz")
