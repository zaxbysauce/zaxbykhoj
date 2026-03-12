"""Static structure checks for LDAP router user-management endpoints."""
import ast
import os


ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'khoj', 'routers', 'ldap.py'
)


def _load_tree():
    with open(ROUTER_PATH, 'r', encoding='utf-8') as f:
        return ast.parse(f.read())


def test_ldap_router_has_user_management_routes():
    tree = _load_tree()

    route_paths = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if isinstance(dec.func.value, ast.Name) and dec.func.value.id == 'router':
                        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                            route_paths.add(dec.args[0].value)

    assert '/api/settings/ldap/users' in route_paths
    assert '/api/settings/ldap/users/{user_id}' in route_paths


def test_ldap_router_has_user_update_model_fields():
    tree = _load_tree()

    fields = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'LdapUserUpdateRequest':
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fields.add(stmt.target.id)

    assert 'is_active' in fields
    assert 'is_admin' in fields


def test_ldap_router_has_managed_user_model():
    tree = _load_tree()

    managed_fields = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'LdapManagedUser':
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    managed_fields.add(stmt.target.id)

    assert {'id', 'username', 'ldap_dn', 'is_active', 'is_admin'}.issubset(managed_fields)


if __name__ == '__main__':
    test_ldap_router_has_user_management_routes()
    test_ldap_router_has_user_update_model_fields()
    test_ldap_router_has_managed_user_model()
    print('All LDAP router structure tests passed.')
