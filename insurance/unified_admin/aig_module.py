import os

from flask import Blueprint, abort, g, redirect, send_from_directory

aig_bp = Blueprint("aig", __name__, url_prefix="/aig")

# The AIG prototype pages live at the repository root, two levels up from this
# package (insurance/unified_admin/ -> insurance/ -> repo root).
AIG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "AIG"))

LOGIN_PAGE = "SSO/Login/GUI/Frmlogin.html"
DASHBOARD_PAGE = "Insurance/GUI/FrmInsurance.html"


@aig_bp.route("/")
def index():
    if g.get("current_user"):
        return redirect(f"/aig/{DASHBOARD_PAGE}")
    return redirect(f"/aig/{LOGIN_PAGE}")


@aig_bp.route("/<path:subpath>")
def serve(subpath):
    # The login page is public; every other page requires an authenticated session.
    if subpath != LOGIN_PAGE and not g.get("current_user"):
        return redirect(f"/aig/{LOGIN_PAGE}")
    if not os.path.isfile(os.path.join(AIG_ROOT, subpath)):
        abort(404)
    return send_from_directory(AIG_ROOT, subpath)
