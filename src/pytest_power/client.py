"""Dependency injection allows HTTP and asynchronous clients to be mocked."""

import os


def controller_address():
    return os.getenv("CONTROLLER_IP", "controller.test")


def announce_vlan(vlan_id):
    print(f"VLAN {vlan_id} ready")


def fetch_ports(client):
    response = client.get("/ports")
    response.raise_for_status()
    return response.json()["ports"]


async def fetch_ports_async(client):
    response = await client.get("/ports")
    response.raise_for_status()
    return response.json()["ports"]
