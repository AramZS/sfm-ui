from django.test import TestCase
from .models import Collection, CollectionSet, Seed, Credential, Group, User, Harvest, HarvestStat, Warc, default_uuid
from .utils import collection_path as get_collection_path
from .utils import collection_set_path as get_collection_set_path
import serialize
import tempfile
import os
import shutil
from datetime import date, datetime


class SerializeTests(TestCase):
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        group1 = Group.objects.create(name="test_group1")
        self.group2 = Group.objects.create(name="test_group2")
        self.collection_set = CollectionSet.objects.create(group=group1,
                                                           name="test_collection_set")
        self.collection_set_path = get_collection_set_path(self.collection_set, sfm_data_dir=self.data_dir)

        # Now change it to group2
        self.collection_set.group = self.group2
        # Now add a description
        self.collection_set.description = "This is a test collection."
        self.collection_set.save()

        self.user1 = User.objects.create_superuser(username="test_user1", email="test_user@test.com",
                                                   password="test_password")
        self.user2 = User.objects.create_superuser(username="test_user2", email="test_user@test.com",
                                                   password="test_password")
        credential1 = Credential.objects.create(user=self.user1, platform="test_platform",
                                                token='{"key":"key1"}')
        self.credential2 = Credential.objects.create(user=self.user2, platform="test_platform",
                                                     token='{"key":"key2"}')
        # Now change credential2
        self.credential2.token = '{"key":"key1.1"}'
        self.credential2.save()
        self.collection1 = Collection.objects.create(collection_set=self.collection_set,
                                                     name="test_collection",
                                                     harvest_type=Collection.TWITTER_USER_TIMELINE,
                                                     credential=credential1)
        # Now change to credential2
        self.collection1.credential = self.credential2
        self.collection1.save()
        self.collection1_path = get_collection_path(self.collection1, sfm_data_dir=self.data_dir)
        self.collection1_records_path = os.path.join(self.collection1_path, serialize.RECORD_DIR)

        # Seed
        self.seed1 = Seed.objects.create(collection=self.collection1, token='{"token":"token1}', is_active=True)
        # Now change seed1
        self.seed1.token = '{"token":"token1.1}'
        self.seed1.save()
        Seed.objects.create(collection=self.collection1, token='{"token":"token2}', is_active=False)

        # Harvest
        historical_collection = self.collection1.history.all()[0]
        historical_credential = historical_collection.credential.history.all()[0]
        self.harvest1 = Harvest.objects.create(collection=self.collection1,
                                               historical_collection=historical_collection,
                                               historical_credential=historical_credential)

        # Harvest stats
        day1 = date(2016, 5, 20)
        day2 = date(2016, 5, 21)
        HarvestStat.objects.create(harvest=self.harvest1, item="tweets", count=5, harvest_date=day1)
        HarvestStat.objects.create(harvest=self.harvest1, item="users", count=6, harvest_date=day1)
        HarvestStat.objects.create(harvest=self.harvest1, item="tweets", count=7, harvest_date=day2)

        # Warcs
        Warc.objects.create(harvest=self.harvest1, warc_id=default_uuid(), path="/data/warc1.warc.gz", sha1="warc1sha",
                            bytes=10, date_created=datetime.utcnow())
        Warc.objects.create(harvest=self.harvest1, warc_id=default_uuid(), path="/data/warc2.warc.gz", sha1="warc2sha",
                            bytes=11,
                            date_created=datetime.utcnow())

    def tearDown(self):
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)

    def test_serialize(self):
        serializer = serialize.RecordSerializer(data_dir=self.data_dir)
        serializer.serialize_collection_set(self.collection_set)

        # Records files exist
        self.assertTrue(os.path.exists(self.collection1_records_path))
        # collection set, historical collection set, groups
        # collection, historical collection, credentials, historical credentials
        # users, seed, historical seeds
        # harvests, harvest_stats, warcs
        self.assertEqual(13, len(os.listdir(self.collection1_records_path)))

        # Deserialize while collection set already exists
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())
        self.assertEqual(2, CollectionSet.history.count())
        self.assertEqual(1, Collection.objects.count())
        self.assertEqual(2, Collection.history.count())
        self.assertEqual(2, Credential.objects.count())
        self.assertEqual(3, Credential.history.count())
        self.assertEqual(2, User.objects.count())
        self.assertEqual(2, Seed.objects.count())
        self.assertEqual(3, Seed.history.count())
        self.assertEqual(1, Harvest.objects.count())
        self.assertEqual(3, HarvestStat.objects.count())
        self.assertEqual(2, Warc.objects.count())

        deserializer = serialize.RecordDeserializer()
        deserializer.deserialize_collection_set(self.collection_set_path)
        # Nothing should change
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())
        self.assertEqual(2, CollectionSet.history.count())
        self.assertEqual(1, Collection.objects.count())
        self.assertEqual(2, Collection.history.count())
        self.assertEqual(2, Credential.objects.count())
        self.assertEqual(3, Credential.history.count())
        self.assertEqual(2, User.objects.count())
        self.assertEqual(2, Seed.objects.count())
        self.assertEqual(3, Seed.history.count())
        self.assertEqual(1, Harvest.objects.count())
        self.assertEqual(3, HarvestStat.objects.count())
        self.assertEqual(2, Warc.objects.count())

        # Partially clean the database in preparation for deserializing
        Warc.objects.all().delete()
        self.assertEqual(0, Warc.objects.count())

        HarvestStat.objects.all().delete()
        self.assertEqual(0, HarvestStat.objects.count())

        self.harvest1.delete()
        self.assertEqual(0, Harvest.objects.count())

        Seed.objects.all().delete()
        self.assertEqual(0, Seed.objects.count())

        Seed.history.all().delete()
        self.assertEqual(0, Seed.history.count())

        self.collection1.delete()
        self.assertEqual(0, Collection.objects.count())
        Collection.history.all().delete()
        self.assertEqual(0, Collection.history.count())

        # Note that credential1 still exists.
        self.credential2.delete()
        self.assertEqual(1, Credential.objects.count())
        # This is also deleting credential1's history
        Credential.history.all().delete()
        self.assertEqual(0, Credential.history.count())

        self.collection_set.delete()
        self.assertEqual(0, CollectionSet.objects.count())
        CollectionSet.history.all().delete()
        self.assertEqual(0, CollectionSet.history.count())

        self.group2.delete()
        # Note that group1 still exists.
        self.assertEqual(1, Group.objects.count())

        CollectionSet.history.all().delete()
        self.assertEqual(0, CollectionSet.history.count())

        # Note that user1 still exists
        self.user2.delete()
        self.assertEqual(1, User.objects.count())
        self.assertEqual(1, Credential.objects.count())

        # Now deserialize again
        deserializer.deserialize_collection_set(self.collection_set_path)

        # And check the deserialization
        self.assertEqual(2, Group.objects.count())
        self.assertEqual(1, CollectionSet.objects.count())
        self.assertEqual(2, CollectionSet.history.count())
        self.assertEqual(1, Collection.objects.count())
        self.assertEqual(2, Collection.history.count())
        self.assertEqual(2, Credential.objects.count())
        # This is one less since credential1's history was deleted.
        self.assertEqual(2, Credential.history.count())
        self.assertEqual(2, User.objects.count())
        self.assertEqual(2, Seed.objects.count())
        self.assertEqual(3, Seed.history.count())
        self.assertEqual(1, Harvest.objects.count())
        self.assertEqual(3, HarvestStat.objects.count())
        self.assertEqual(2, Warc.objects.count())
