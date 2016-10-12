from django.test import TestCase
from .models import Collection, CollectionSet, Seed, Credential, Group, User, Harvest
from .serialize import RecordSerializer, RecordDeserializer
from django.core import serializers
import json
import tempfile
import os
import shutil
import re

class SerializeTests(TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        group1 = Group.objects.create(name="test_group1")
        self.group2 = Group.objects.create(name="test_group2")
        self.collection_set = CollectionSet.objects.create(group=group1,
                                                           name="test_collection_set")
        # Now change it to group2
        self.collection_set.group = self.group2
        # Now add a description
        self.collection_set.description = "This is a test collection."
        self.collection_set.save()

        credential1 = Credential.objects.create(user=user, platform="test_platform",
                                                    token="{}")

    def tearDown(self):
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)
    #
    # def test_filename(self):
    #     # Model object without last_updated
    #     self.assertRegexpMatches(RecordSerializer._filename(self.group), "Group-test_group.json")
    #     # Model object with uuid
    #     self.assertEqual("CollectionSet-{}.json".format(self.collection_set.collection_set_id),
    #                      RecordSerializer._filename(self.collection_set))
    #     # Model object with other object as natural keys
    #     historical_collection_set = self.collection_set.history.all()[0]
    #     self.assertEqual("HistoricalCollectionSet-{}-{}.json".format(historical_collection_set.collection_set_id,
    #                                                                  RecordSerializer._date_format(
    #                                                                      historical_collection_set.history_date)),
    #                      RecordSerializer._filename(historical_collection_set))

    def test_serialize(self):
        serializer = RecordSerializer(self.collection_set, self.data_dir)
        serializer.serialize()

        # groups.json exists.
        self.assertTrue(serializer.group_record_filepath)
        # collection_sets.json exists
        self.assertTrue(serializer.collections_set_record_filepath)

        # Deserialize while collection set already exists
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())
        self.assertEqual(2, CollectionSet.history.count())

        deserializer = RecordDeserializer(serializer.collection_set_path)
        deserializer.deserialize()
        # Nothing should change
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())

        # Partially clean the database in preparation for deserializing
        self.collection_set.delete()
        self.group2.delete()
        # Note that group1 still exists.
        self.assertEqual(1, Group.objects.count())
        self.assertEqual(0, CollectionSet.objects.count())
        # TODO: Delete history
        self.assertEqual(3, CollectionSet.history.count())

        # Now deserialize
        # deserializer = RecordDeserializer(serializer.collection_set_path)
        deserializer.deserialize()

        # And check the deserialization
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())
        self.assertEqual(5, CollectionSet.history.count())

#     def test_serialize_collection_set(self):
#
#         data = serializers.serialize("json", [self.collection_set, ], indent=4, use_natural_foreign_keys=True,
#                                      use_natural_primary_keys=True)
#         # print json.dumps(data, indent=4)
#         print data
#
#     def test_deserialize_collection_set(self):
#         collection_set_str = """
# [
# {
#     "fields": {
#         "is_visible": true,
#         "group": [
#             "test_group"
#         ],
#         "name": "test_collection_set",
#         "date_updated": "2016-09-29T20:49:44.931Z",
#         "history_note": "",
#         "date_added": "2016-09-29T20:49:44.931Z",
#         "collection_set_id": "f31cc5bd10f24c26bef021fd9a5d8ea9",
#         "description": "This is a test collection."
#     },
#     "model": "ui.collectionset"
# }
# ]
#         """
#
#         list(serializers.deserialize("json", collection_set_str))[0].save()
#         collection_set = CollectionSet.objects.get(collection_set_id="f31cc5bd10f24c26bef021fd9a5d8ea9")
#         self.assertTrue(collection_set.is_visible)
#         self.assertEqual("This is a test collection.", collection_set.description)
#         self.assertEqual(self.group1, collection_set.group)
#
#     def test_serialize_collection_set_history(self):
#         data = serializers.serialize("json", self.collection_set.history.all(), indent=4, use_natural_foreign_keys=True,
#                                      use_natural_primary_keys=True)
#         # print json.dumps(data, indent=4)
#         print data
