from __future__ import annotations

from inspect import iscoroutinefunction

from fastapi.routing import APIRoute

from app.api.app import create_app


def test_api_routes_and_dependencies_are_async_to_avoid_threadpool_deadlock():
    app = create_app()

    sync_endpoints: list[str] = []
    sync_dependencies: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not iscoroutinefunction(route.endpoint):
            sync_endpoints.append(route.path)
        for dependency in route.dependant.dependencies:
            dependency_call = dependency.call
            if dependency_call is not None and not iscoroutinefunction(dependency_call):
                sync_dependencies.append(f"{route.path}:{getattr(dependency_call, '__name__', repr(dependency_call))}")

    assert sync_endpoints == []
    assert sync_dependencies == []
