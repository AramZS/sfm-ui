from django.test import TestCase
from .models import Collection, CollectionSet, Seed, Credential, Group, User, Harvest
from django.core import serializers
import json

class SerializeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="test_user", email="test_user@test.com",
                                                  password="test_password")
        self.group = Group.objects.create(name="test_group")
        self.collection_set = CollectionSet.objects.create(group=self.group, name="test_collection_set")

    def test_serialize_collection_set(self):
        data = serializers.serialize("json", [self.collection_set,], indent=4, use_natural_foreign_keys=True, use_natural_primary_keys=True)
        # print json.dumps(data, indent=4)
        print data

    def test_deserialize_collection_set(self):
        collection_set_str = """
[
{
    "fields": {
        "is_visible": true,
        "group": [
            "test_group"
        ],
        "name": "test_collection_set",
        "date_updated": "2016-09-29T20:49:44.931Z",
        "history_note": "",
        "date_added": "2016-09-29T20:49:44.931Z",
        "collection_set_id": "f31cc5bd10f24c26bef021fd9a5d8ea9",
        "description": "This is a test collection."
    },
    "model": "ui.collectionset"
}
]
        """

        list(serializers.deserialize("json", collection_set_str))[0].save()
        collection_set = CollectionSet.objects.get(collection_set_id="f31cc5bd10f24c26bef021fd9a5d8ea9")
        self.assertTrue(collection_set.is_visible)
        self.assertEqual("This is a test collection.", collection_set.description)
        self.assertEqual(self.group, collection_set.group)

    def test_serialize_collection_set_history(self):
        data = serializers.serialize("json", self.collection_set.history.all(), indent=4, use_natural_foreign_keys=True,
                                     use_natural_primary_keys=True)
        # print json.dumps(data, indent=4)
        print data