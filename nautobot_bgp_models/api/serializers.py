"""REST API serializers for nautobot_bgp_models models."""

from rest_framework import serializers

from nautobot.dcim.api.serializers import NestedDeviceSerializer, NestedInterfaceSerializer
from nautobot.ipam.api.serializers import NestedVRFSerializer, NestedIPAddressSerializer
from nautobot.extras.api.customfields import CustomFieldModelSerializer
from nautobot.extras.api.serializers import TaggedObjectSerializer, StatusModelSerializerMixin, NestedSecretSerializer
from nautobot.core.settings_funcs import is_truthy

from nautobot.circuits.api.serializers import NestedProviderSerializer

from nautobot_bgp_models import models

# We have to do this wildcard import of nested_serializers for the "brief" API parameter to work automatically.
from .nested_serializers import *  # noqa:F401,F403 pylint: disable=wildcard-import,unused-wildcard-import


class AutonomousSystemSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    """REST API serializer for AutonomousSystem records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:autonomoussystem-detail")
    provider = NestedProviderSerializer(required=False, allow_null=True)

    class Meta:
        model = models.AutonomousSystem
        fields = ["id", "url", "asn", "description", "status", "provider", "tags"]


class PeeringRoleSerializer(CustomFieldModelSerializer):
    """REST API serializer for PeeringRole records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:peeringrole-detail")

    class Meta:
        model = models.PeeringRole
        fields = ["id", "url", "name", "slug", "color", "description"]


class InheritableFieldsSerializerMixin:
    """Common mixin for Serializers that support an additional `include_inherited` query parameter."""

    def to_representation(self, instance):
        """Render the model instance to a Python dict.

        If `include_inherited` is specified as a request parameter, include inherited field values as appropriate.
        """
        req = self.context["request"]
        if hasattr(req, "query_params") and is_truthy(req.query_params.get("include_inherited", False)):
            inherited_fields = instance.get_fields(include_inherited=True)
            for field, data in inherited_fields.items():
                setattr(instance, field, data["value"])
        return super().to_representation(instance)


class ExtraAttributesSerializerMixin(serializers.Serializer):  # pylint: disable=abstract-method
    """Common mixin for BGP Extra Attributes."""

    extra_attributes = serializers.SerializerMethodField(read_only=True)

    def get_extra_attributes(self, instance):
        """Return either the `display` property of the instance or `str(instance)`."""
        req = self.context["request"]

        if hasattr(req, "query_params") and is_truthy(req.query_params.get("include_inherited", False)):
            return instance.get_extra_attributes()

        return instance.extra_attributes


class PeerGroupTemplateSerializer(CustomFieldModelSerializer, ExtraAttributesSerializerMixin):
    """REST API serializer for PeerGroup records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:peergrouptemplate-detail")

    autonomous_system = NestedAutonomousSystemSerializer(required=False, allow_null=True)
    secret = NestedSecretSerializer(required=False, allow_null=True)

    class Meta:
        model = models.PeerGroupTemplate
        fields = [
            "id",
            "url",
            "name",
            "role",
            "description",
            "enabled",
            "autonomous_system",
            "import_policy",
            "export_policy",
            "secret",
        ]


class PeerGroupSerializer(InheritableFieldsSerializerMixin, CustomFieldModelSerializer, ExtraAttributesSerializerMixin):
    """REST API serializer for PeerGroup records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:peergroup-detail")
    source_ip = NestedIPAddressSerializer(required=False, allow_null=True)  # noqa: F405
    source_interface = NestedInterfaceSerializer(required=False, allow_null=True)  # noqa: F405

    routing_instance = NestedRoutingInstanceSerializer(required=True)

    autonomous_system = NestedAutonomousSystemSerializer(required=False, allow_null=True)

    template = NestedPeerGroupTemplateSerializer(required=False, allow_null=True)

    secret = NestedSecretSerializer(required=False, allow_null=True)

    class Meta:
        model = models.PeerGroup
        fields = [
            "id",
            "url",
            "name",
            "source_ip",
            "source_interface",
            "description",
            "enabled",
            "autonomous_system",
            "routing_instance",
            "template",
            "secret",
            "extra_attributes",
            "role",
            "import_policy",
            "export_policy",
        ]


class PeerEndpointSerializer(
    InheritableFieldsSerializerMixin,
    TaggedObjectSerializer,
    CustomFieldModelSerializer,
    ExtraAttributesSerializerMixin,
):
    """REST API serializer for PeerEndpoint records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:peerendpoint-detail")
    source_ip = NestedIPAddressSerializer(required=False, allow_null=True)  # noqa: F405
    source_interface = NestedInterfaceSerializer(required=False, allow_null=True)  # noqa: F405
    peer = NestedPeerEndpointSerializer(required=False, allow_null=True)  # noqa: F405
    peering = NestedPeeringSerializer(required=True, allow_null=True)  # noqa: F405
    peer_group = NestedPeerGroupSerializer(required=False, allow_null=True)
    routing_instance = NestedRoutingInstanceSerializer(required=False, allow_null=True)
    autonomous_system = NestedAutonomousSystemSerializer(required=False, allow_null=True)
    secret = NestedSecretSerializer(required=False, allow_null=True)

    class Meta:
        model = models.PeerEndpoint
        fields = [
            "id",
            "url",
            "routing_instance",
            "source_ip",
            "source_interface",
            "autonomous_system",
            "peer_group",
            "peer",
            "import_policy",
            "export_policy",
            "peering",
            "secret",
            "tags",
            "enabled",
        ]

    def create(self, validated_data):
        """Create a new PeerEndpoint and update the peer on both sides."""
        record = super().create(validated_data)
        record.peering.update_peers()
        return record

    def update(self, instance, validated_data):
        """When updating an existing PeerEndpoint, ensure peer is properly setup on both side."""
        peering_has_been_updated = False
        if instance.peering.pk != validated_data.get("peering"):
            peering_has_been_updated = True

        result = super().update(instance, validated_data)

        if peering_has_been_updated:
            result.peering.update_peers()

        return result


class BGPRoutingInstanceSerializer(CustomFieldModelSerializer, ExtraAttributesSerializerMixin):
    """REST API serializer for Peering records."""

    url = serializers.HyperlinkedIdentityField(
        view_name="plugins-api:nautobot_bgp_models-api:bgproutinginstance-detail"
    )

    endpoints = NestedPeerEndpointSerializer(required=False, many=True)  # noqa: F405

    device = NestedDeviceSerializer()

    autonomous_system = NestedAutonomousSystemSerializer(required=False, allow_null=True)

    router_id = NestedIPAddressSerializer(required=False, allow_null=True)  # noqa: F405

    class Meta:
        model = models.BGPRoutingInstance
        fields = [
            "id",
            "url",
            "device",
            "description",
            "router_id",
            "autonomous_system",
            "endpoints",
        ]


class PeeringSerializer(CustomFieldModelSerializer, StatusModelSerializerMixin):
    """REST API serializer for Peering records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:peering-detail")

    endpoints = NestedPeerEndpointSerializer(required=False, many=True)  # noqa: F405

    class Meta:
        model = models.Peering
        fields = [
            "id",
            "url",
            "status",
            "endpoints",
        ]


class AddressFamilySerializer(CustomFieldModelSerializer):
    """REST API serializer for AddressFamily records."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:nautobot_bgp_models-api:addressfamily-detail")

    routing_instance = NestedRoutingInstanceSerializer(required=True)

    vrf = NestedVRFSerializer(required=False, allow_null=True)

    class Meta:
        model = models.AddressFamily
        fields = [
            "id",
            "url",
            "afi_safi",
            "routing_instance",
            "vrf",
            "export_policy",
            "import_policy",
        ]
