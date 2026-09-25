"""An in-memory fake: realistic state transitions without any network I/O."""

from dataclasses import asdict, dataclass
import logging
import warnings

log = logging.getLogger(__name__)


class TopologyError(ValueError):
    """An invalid operation on the simulated topology."""


@dataclass(frozen=True)
class Vlan:
    vlan_id: int
    ports: tuple[str, ...]
    protocol: str = "1.3"


class FakeController:
    def __init__(self, ports=("eth1", "eth2"), *, address="controller.test", strict=False):
        self.address = address  # Metadata only; never used to open a connection.
        self.strict = strict
        self.ports = dict.fromkeys(ports, True)
        self.vlans: dict[int, Vlan] = {}
        self.events: list[str] = []
        self.closed = False

    def create_vlan(self, vlan_id, ports, protocol="1.3"):
        ports = tuple(ports)
        if self.closed:
            raise TopologyError("Controller closed")
        if type(vlan_id) is not int or not 1 <= vlan_id <= 4094:
            raise TopologyError("VLAN must be an integer between 1 and 4094")
        if vlan_id in self.vlans:
            raise TopologyError(f"VLAN {vlan_id} already exists")
        if protocol not in {"1.3", "1.5"}:
            raise TopologyError(f"Unsupported OpenFlow protocol: {protocol}")
        if not ports or len(set(ports)) != len(ports):
            raise TopologyError("Provide distinct ports")
        for port in ports:
            if port not in self.ports:
                raise TopologyError(f"Unknown port: {port}")
            if not self.ports[port]:
                raise TopologyError(f"Port Down: {port}")
        if self.strict and len(ports) < 2:
            raise TopologyError("Strict mode requires at least two ports")
        vlan = Vlan(vlan_id, ports, protocol)
        self.vlans[vlan_id] = vlan
        self.events.append(f"create:{vlan_id}")
        log.info("Created VLAN %s using OpenFlow %s", vlan_id, protocol)
        return vlan

    def delete_vlan(self, vlan_id):
        if self.vlans.pop(vlan_id, None) is not None:
            self.events.append(f"delete:{vlan_id}")
            log.info("Deleted VLAN %s", vlan_id)

    def reachable(self, vlan_id):
        vlan = self.vlans.get(vlan_id)
        return bool(not self.closed and vlan and all(self.ports[p] for p in vlan.ports))

    def snapshot(self):
        return {
            "address": self.address,
            "ports": dict(self.ports),
            "vlans": {str(key): asdict(value) for key, value in self.vlans.items()},
            "events": list(self.events),
            "closed": self.closed,
        }

    def legacy_port_names(self):
        warnings.warn("Use controller.ports instead", DeprecationWarning, stacklevel=2)
        return list(self.ports)

    def create_qinq(self, outer, inner):
        """Deliberately unsupported to illustrate strict xfail."""
        raise NotImplementedError("QinQ is not implemented in this fake")

    def close(self):
        self.vlans.clear()
        self.closed = True


def provision_verified(controller, vlan_id, ports, protocol="1.3"):
    """Roll back a newly created VLAN if verification fails or raises."""
    vlan = controller.create_vlan(vlan_id, ports, protocol=protocol)
    try:
        if not controller.reachable(vlan_id):
            raise TopologyError(f"VLAN {vlan_id} is unreachable")
    except Exception:
        controller.delete_vlan(vlan_id)
        raise
    return vlan


def attenuation(input_dbm, output_dbm):
    return input_dbm - output_dbm
