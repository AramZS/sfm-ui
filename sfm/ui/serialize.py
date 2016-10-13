import datetime
import os
import shutil
import codecs
import logging
import json

from django.core import serializers

from sfmutils.utils import safe_string
from .utils import collection_path as get_collection_path
from .models import Group, CollectionSet, Collection, User, Credential

log = logging.getLogger(__name__)

RECORD_DIR = "records"
GROUP_FILENAME = "groups.json"
COLLECTION_SET_FILENAME = "collection_set.json"
HISTORICAL_COLLECTION_SET_FILENAME = "historical_collection_set.json"
CREDENTIAL_FILENAME = "credentials.json"
HISTORICAL_CREDENTIAL_FILENAME = "historical_credentials.json"
COLLECTION_FILENAME = "collection.json"
HISTORICAL_COLLECTION_FILENAME = "historical_collection.json"
USER_FILENAME = "users.json"
SEED_FILENAME = "seeds.json"
HISTORICAL_SEED_FILENAME = "historical_seeds.json"
HARVEST_FILENAME = "harvests.json"
HARVEST_STATS_FILENAME = "harvest_stats.json"
WARC_FILENAME = "warcs.json"


class RecordSerializer:
    def __init__(self, data_dir=None):
        log.debug("Data dir is %s", data_dir)
        self.data_dir = data_dir

    def serialize_collection_set(self, collection_set):
        for collection in collection_set.collections.all():
            self.serialize_collection(collection)

    def serialize_collection(self, collection):
        records_path = os.path.join(get_collection_path(collection, sfm_data_dir=self.data_dir), RECORD_DIR)
        log.debug("Collection records path is %s", records_path)

        # Initialize records dir
        self._initialize_records_dir(records_path)

        # Serialize collection set, historical collection sets, and groups
        self._serialize_collection_set(collection.collection_set, records_path)

        # Serialize credentials and users
        self._serialize_credentials(collection, records_path)

        # Collection
        collection_record_filepath = os.path.join(records_path, COLLECTION_FILENAME)
        self._serialize_objs((collection,), collection_record_filepath)
        log.debug("Serialized collection to %s", collection_record_filepath)

        # Historical collection
        historical_collection_record_filepath = os.path.join(records_path, HISTORICAL_COLLECTION_FILENAME)
        self._serialize_objs(collection.history.all(), historical_collection_record_filepath)
        log.debug("Serialized historical collection to %s", historical_collection_record_filepath)

        # Seeds
        self._serialize_seeds(collection, records_path)

        # Harvests, harvest stats, and warcs
        self._serialize_harvests(collection, records_path)

    def _serialize_collection_set(self, collection_set, records_path):
        # Groups
        self._serialize_groups(collection_set, records_path)

        # Collection set
        collection_set_record_filepath = os.path.join(records_path, COLLECTION_SET_FILENAME)
        self._serialize_objs((collection_set,), collection_set_record_filepath)
        log.debug("Serialized collection set to %s", collection_set_record_filepath)

        # Historical collection set
        historical_collection_set_record_filepath = os.path.join(records_path, HISTORICAL_COLLECTION_SET_FILENAME)
        self._serialize_objs(collection_set.history.all(), historical_collection_set_record_filepath)
        log.debug("Serialized historical collection sets to %s", historical_collection_set_record_filepath)

    def _serialize_groups(self, collection_set, records_path):
        # Groups (current group and all groups in historical collection sets)
        groups = {collection_set.group,}
        for historical_collection_set in collection_set.history.all():
            groups.add(historical_collection_set.group)
        group_record_filepath = os.path.join(records_path, GROUP_FILENAME)
        self._serialize_objs(groups, group_record_filepath)
        log.debug("Serialized groups to %s", group_record_filepath)

    def _serialize_credentials(self, collection, records_path):
        # Credentials (current credential and all credentials in historical collections
        credentials = {collection.credential}
        for historical_collection in collection.history.all():
            credentials.add(historical_collection.credential)

        credentials_record_filepath = os.path.join(records_path, CREDENTIAL_FILENAME)
        self._serialize_objs(credentials, credentials_record_filepath)
        log.debug("Serialized credentials to %s", credentials_record_filepath)

        # Historical credentials
        historical_credentials_record_filepath = os.path.join(records_path, HISTORICAL_CREDENTIAL_FILENAME)
        self._serialize_objs(self._historical_credentials_iter(credentials), historical_credentials_record_filepath)
        log.debug("Serialized historical credentials to %s", historical_credentials_record_filepath)

        # Users
        self._serialize_users(credentials, records_path)

    @staticmethod
    def _historical_credentials_iter(credentials):
        for credential in credentials:
            for historical_credential in credential.history.all():
                yield historical_credential

    def _serialize_users(self, credentials, records_path):
        users = set()
        for credential in credentials:
            users.add(credential.user)
        # TODO: Change password
        user_record_filepath = os.path.join(records_path, USER_FILENAME)
        self._serialize_objs(users, user_record_filepath)
        log.debug("Serialized users to %s", user_record_filepath)

    def _serialize_seeds(self, collection, records_path):
        # Seeds
        seeds_record_filepath = os.path.join(records_path, SEED_FILENAME)
        self._serialize_objs(collection.seeds.all(), seeds_record_filepath)
        log.debug("Serialized seeds to %s", seeds_record_filepath)

        # Historical seeds
        historical_seeds_record_filepath = os.path.join(records_path, HISTORICAL_SEED_FILENAME)
        self._serialize_objs(self._historical_seeds_iter(collection), historical_seeds_record_filepath)
        log.debug("Serialized historical seeds to %s", historical_seeds_record_filepath)

    @staticmethod
    def _historical_seeds_iter(collection):
        for seed in collection.seeds.all():
            for historical_seed in seed.history.all():
                yield historical_seed

    def _serialize_harvests(self, collection, records_path):
        # Harvests
        harvests_record_filepath = os.path.join(records_path, HARVEST_FILENAME)
        self._serialize_objs(collection.harvests.all(), harvests_record_filepath)
        log.debug("Serialized harvests to %s", harvests_record_filepath)

        # Harvest stats
        harvest_stats_record_filepath = os.path.join(records_path, HARVEST_STATS_FILENAME)
        self._serialize_objs(self._harvest_stats_iter(collection), harvest_stats_record_filepath)
        log.debug("Serialized harvest stats to %s", harvest_stats_record_filepath)

        # WARCs
        warc_record_filepath = os.path.join(records_path, WARC_FILENAME)
        self._serialize_objs(self._warcs_iter(collection), warc_record_filepath)
        log.debug("Serialized warcs to %s", warc_record_filepath)

    @staticmethod
    def _harvest_stats_iter(collection):
        for harvest in collection.harvests.all():
            for harvest_stats in harvest.harvest_stats.all():
                yield harvest_stats

    @staticmethod
    def _warcs_iter(collection):
        for harvest in collection.harvests.all():
            for warc in harvest.warcs.all():
                yield warc

    @staticmethod
    def _initialize_records_dir(records_path):
        if os.path.exists(records_path):
            shutil.rmtree(records_path)
        os.makedirs(records_path)

    def _serialize_objs(self, objs, filepath):
        with codecs.open(filepath, "w") as f:
            serializers.serialize("json", objs, indent=4, use_natural_foreign_keys=True,
                                     use_natural_primary_keys=True, stream=f)
        assert os.path.exists(filepath)


class RecordDeserializer:
    def __init__(self):
        pass

    @staticmethod
    def _check_exists(filepath):
        if not os.path.exists(filepath):
            raise IOError("{} not found".format(filepath))

    def deserialize_collection_set(self, collection_set_path):
        log.info("Deserializing collection set at %s", collection_set_path)
        self._check_exists(collection_set_path)
        for pathname in os.listdir(collection_set_path):
            collection_path = os.path.join(collection_set_path, pathname)
            if os.path.isdir(collection_path):
                records_path = os.path.join(collection_path, RECORD_DIR)
                if os.path.exists(records_path):
                    self.deserialize_collection(collection_path)
                else:
                    log.debug("%s is not a collection", collection_path)

    def deserialize_collection(self, collection_path):
        log.info("Deserializing collection at %s", collection_path)

        # Determine paths and make sure they exist before deserializing
        records_path = os.path.join(collection_path, RECORD_DIR)
        self._check_exists(records_path)

        group_record_filepath = os.path.join(records_path, GROUP_FILENAME)
        self._check_exists(group_record_filepath)

        collection_set_record_filepath = os.path.join(records_path, COLLECTION_SET_FILENAME)
        self._check_exists(collection_set_record_filepath)

        historical_collection_set_record_filepath = os.path.join(records_path, HISTORICAL_COLLECTION_SET_FILENAME)
        self._check_exists(historical_collection_set_record_filepath)

        collection_record_filepath = os.path.join(records_path, COLLECTION_FILENAME)
        self._check_exists(collection_record_filepath)

        historical_collection_record_filepath = os.path.join(records_path, HISTORICAL_COLLECTION_FILENAME)
        self._check_exists(historical_collection_record_filepath)

        user_record_filepath = os.path.join(records_path, USER_FILENAME)
        self._check_exists(user_record_filepath)

        credential_record_filepath = os.path.join(records_path, CREDENTIAL_FILENAME)
        self._check_exists(credential_record_filepath)

        historical_credential_record_filepath = os.path.join(records_path, HISTORICAL_CREDENTIAL_FILENAME)
        self._check_exists(historical_credential_record_filepath)

        seed_filepath = os.path.join(records_path, SEED_FILENAME)
        self._check_exists(seed_filepath)

        historical_seed_filepath = os.path.join(records_path, HISTORICAL_SEED_FILENAME)
        self._check_exists(historical_seed_filepath)

        harvest_filepath = os.path.join(records_path, HARVEST_FILENAME)
        self._check_exists(harvest_filepath)

        harvest_stats_filepath = os.path.join(records_path, HARVEST_STATS_FILENAME)
        self._check_exists(harvest_stats_filepath)

        warcs_filepath = os.path.join(records_path, WARC_FILENAME)
        self._check_exists(warcs_filepath)

        print json.dumps(self._load_record(harvest_filepath), indent=4)

        # Only proceed with deserialization if collection doesn't already exist
        collection_id = self._load_record(collection_record_filepath)[0]["fields"]["collection_id"]
        if not Collection.objects.filter(collection_id=collection_id).exists():
            log.debug("Collection does not exist, so proceeding with deserialization")

            # Only proceed with deserialization of collection set if it doesn't already exist
            collection_set_id = self._load_record(collection_set_record_filepath)[0]["fields"]["collection_set_id"]
            if not CollectionSet.objects.filter(collection_set_id=collection_set_id).exists():
                log.debug("Collection set does not exist, so proceeding with deserialization")

                # Groups first
                self._deserialize_groups(group_record_filepath)

                # Collection set
                self._deserialize(collection_set_record_filepath)

                # Historical collection set
                self._deserialize(historical_collection_set_record_filepath)

            else:
                log.warning("Collection set already exists, so not deserializing")

            # Users
            self._deserialize_users(user_record_filepath)

            # Credentials and credential history
            self._deserialize_credentials(credential_record_filepath, historical_credential_record_filepath)

            # Collection
            self._deserialize(collection_record_filepath)

            # Collection history
            self._deserialize(historical_collection_record_filepath)

            # Seeds
            self._deserialize(seed_filepath)

            # Historical seeds
            self._deserialize(historical_seed_filepath)

            # Harvests
            self._deserialize(harvest_filepath)

            # Harvest stats
            self._deserialize(harvest_stats_filepath)

            # Warcs
            self._deserialize(warcs_filepath)

        else:
            log.warning("Collection already exists, so not deserializing")

    def _deserialize_groups(self, group_record_filepath):
        log.debug("Deserializing groups")
        for d_group in self._deserialize_iter(group_record_filepath):
            if not Group.objects.filter(name=d_group.object.name).exists():
                log.debug("Saving group %s", d_group.object.name)
                d_group.save()
            else:
                log.debug("Group %s already exists", d_group.object.name)

    def _deserialize_users(self, user_record_filepath):
        log.debug("Deserializing users")
        for d_user in self._deserialize_iter(user_record_filepath):
            if not User.objects.filter(username=d_user.object.username).exists():
                log.debug("Saving group %s", d_user.object.username)
                d_user.save()
            else:
                log.debug("User %s already exists", d_user.object.username)

    def _deserialize_credentials(self, credentials_record_filepath, historical_credentials_record_filepath):
        log.debug("Deserializing credentials")
        print len(Credential.objects.all())
        for c in Credential.objects.all():
            print c.credential_id
        credential_ids = []
        for d_credential in self._deserialize_iter(credentials_record_filepath):
            if not Credential.objects.filter(credential_id=d_credential.object.credential_id).exists():
                log.debug("Saving credential %s", d_credential.object.credential_id)
                d_credential.save()
                credential_ids.append(d_credential.object.credential_id)
            else:
                log.debug("Credential %s already exists", d_credential.object.credential_id)

        for d_historical_credential in self._deserialize_iter(historical_credentials_record_filepath):
            if d_historical_credential.object.instance.credential_id in credential_ids:
                log.debug("Saving historical credential %s (%s)", d_historical_credential.object.instance.credential_id, d_historical_credential.object.history_date)
                d_historical_credential.save()

    def _load_record(self, record_filepath):
        with codecs.open(record_filepath, "r") as f:
            record = json.load(f)
        return record

    # def deserialize(self):
    #     # Groups
    #     self.deserialize_groups()
    #
    #     deserialized_collection_set = self._load_collection_set()
    #     # If collection set exists, deserialize nothing else
    #     if not CollectionSet.objects.filter(collection_set_id=deserialized_collection_set.object.collection_set_id).exists():
    #         log.debug("Collection set does not exist, so proceeding with deserialization")
    #
    #         # Save the collection set
    #         deserialized_collection_set.save()
    #
    #         # Historical collection sets
    #         self._deserialize(self.historical_collections_set_record_filepath)
    #
    #     else:
    #         log.warning("Not loading from %s since collection set already exists", self.collection_set_path)
    #
    # def _load_collection_set(self):
    #     return self._deserialize_iter(self.collections_set_record_filepath).next()
    #

    def _deserialize_item(self, record_filepath):
        return self._deserialize_iter(record_filepath).next()

    def _deserialize(self, filepath):
        for d_obj in self._deserialize_iter(filepath):
            d_obj.save()

    @staticmethod
    def _deserialize_iter(filepath):
        log.debug("Deserializing %s", filepath)
        with codecs.open(filepath, "r") as f:
            for d_obj in serializers.deserialize("json", f):
                yield d_obj
