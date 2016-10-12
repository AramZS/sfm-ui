import datetime
import os
import shutil
import codecs
import logging

from django.core import serializers

from sfmutils.utils import safe_string
from .utils import collection_path, collection_set_path
from .models import Group, CollectionSet

log = logging.getLogger(__name__)

RECORD_DIR = "records"
GROUP_FILENAME = "groups.json"
COLLECTION_SET_FILENAME = "collection_set.json"
HISTORICAL_COLLECTION_SET_FILENAME = "historical_collection_set.json"
CREDENTIAL_FILENAME = "credentials.json"

class RecordSerializer:
    def __init__(self, collection_set, data_dir=None):
        self.data_dir = data_dir
        # self.collection_set = collection_set
        # self.collection_set_path = collection_set_path(collection_set, sfm_data_dir=data_dir)
        # self.collection_set_records_path = os.path.join(self.collection_set_path,
        #                                                RECORD_DIR)
        # log.debug("Collection set records path is %s", self.collection_set_records_path)
        # self.group_record_filepath = os.path.join(self.collection_set_records_path, GROUP_FILENAME)
        # self.collections_set_record_filepath = os.path.join(self.collection_set_records_path, COLLECTION_SET_FILENAME)
        # self.historical_collections_set_record_filepath = os.path.join(self.collection_set_records_path, HISTORICAL_COLLECTION_SET_FILENAME)
        #
        # self.collection_path_dict = {}
        # self.collection_records_path_dict = {}
        # self.credential_record_filepath_dict = {}
        # for collection in self.collection_set.collections.all():
        #     self.collection_path_dict[collection] = collection_path(collection, sfm_data_dir=data_dir)
        #     self.collection_records_path_dict[collection] = os.path.join(self.collection_path_dict[collection], RECORD_DIR)
        #     self.credential_record_filepath_dict[collection] = os.path.join(self.collection_records_path_dict[collection], CREDENTIAL_FILENAME)

    def serialize_collection_set(self, collection_set):
        for collection in collection_set.collections.all():
            self.serialize_collection(collection)

    def serialize_collection(self, collection):
        records_path = collection_path(collection, sfm_data_dir=self.data_dir)
        log.debug("Collection records path is %s", records_path)
        # Initialize records dir
        self._initialize_records_dir(records_path)

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
        groups = set((self.collection_set.group,))
        for historical_collection_set in collection_set.history.all():
            groups.add(historical_collection_set.group)
        group_record_filepath = os.path.join(records_path, GROUP_FILENAME)
        self._serialize_objs(groups, group_record_filepath)
        log.debug("Serialized groups to %s", group_record_filepath)

    # def serialize(self):
    #     # Initialize record dir for collection set
    #     self._initialize_records_dir(self.collection_set_records_path)
    #     # Groups (current group and all groups in historical collection sets)
    #     self.serialize_groups()
    #     # Collection set
    #     self._serialize_objs((self.collection_set,), self.collections_set_record_filepath)
    #     # Historical collection sets
    #     self._serialize_objs(self.collection_set.history.all(), self.historical_collections_set_record_filepath)
    #     # For each collection:
    #     for collection in self.collection_set.collections.all():
    #         # For each credential (current credential and credentials in historical collections):
    #         # Credential and historical credentials
    #         self.serialize_credentials(collection)
    #         # Collection
    #         # Historical collections
    #         # For each seed:
    #         # Seed
    #         # Historical seeds
    #         # For each harvest:
    #         # Harvest
    #         # Harvest stats
    #         # Warcs


    @staticmethod
    def _initialize_records_dir(records_path):
        if os.path.exists(records_path):
            shutil.rmtree(records_path)
        os.makedirs(records_path)

    # def serialize_groups(self):
    #     groups = set((self.collection_set.group,))
    #     for historical_collection_set in self.collection_set.history.all():
    #         groups.add(historical_collection_set.group)
    #     self._serialize_objs(groups, self.group_record_filepath)

    def _serialize_objs(self, objs, filepath):
        log.debug("Serializing %s objects to %s", len(objs), filepath)
        with codecs.open(filepath, "w") as f:
            serializers.serialize("json", objs, indent=4, use_natural_foreign_keys=True,
                                     use_natural_primary_keys=True, stream=f)
        assert os.path.exists(filepath)

    # def serialize_credentials(self, collection):
    #     credentials = set((collection.credential,))
    #     for historical_collection in collection.history.all():
    #         credentials.add(historical_collection.credential)
    #     self._serialize_objs(credentials, self.credential_record_filepath_dict[collection])
    # @staticmethod
    # def _filename(obj):
    #     filename_parts = [obj.__class__.__name__]
    #     filename_parts.extend(RecordSerializer._filename_parts(obj))
    #     # filename_parts.append(RecordSerializer._date_format(RecordSerializer._date_updated(obj)))
    #     return "{}.json".format("-".join(filename_parts))
    #
    # @staticmethod
    # def _filename_parts(obj):
    #     filename_parts = []
    #     if hasattr(obj, "natural_key"):
    #         for key_obj in obj.natural_key():
    #             filename_parts.extend(RecordSerializer._filename_parts(key_obj))
    #     elif isinstance(obj, datetime.datetime):
    #         filename_parts.append(RecordSerializer._date_format(obj))
    #     else:
    #         filename_parts.append(safe_string(obj))
    #     return filename_parts
    #
    # @staticmethod
    # def _date_format(dt):
    #     return '{:%Y%m%d%H%M%S}'.format(dt)

class RecordDeserializer:
    def __init__(self, collection_set_path):
        self.collection_set_path = collection_set_path

        self.collection_set_records_path = os.path.join(collection_set_path, RECORD_DIR)
        log.debug("Collection set records path is %s", self.collection_set_records_path)
        self.group_record_filepath = os.path.join(self.collection_set_records_path, GROUP_FILENAME)
        self.collections_set_record_filepath = os.path.join(self.collection_set_records_path, COLLECTION_SET_FILENAME)
        self.historical_collections_set_record_filepath = os.path.join(self.collection_set_records_path, HISTORICAL_COLLECTION_SET_FILENAME)

        self._check_exists(self.collection_set_records_path)
        self._check_exists(self.group_record_filepath)
        self._check_exists(self.collections_set_record_filepath)
        self._check_exists(self.historical_collections_set_record_filepath)

    def _check_exists(self, filepath):
        if not os.path.exists(filepath):
            raise IOError("{} not found".format(filepath))

    def deserialize(self):
        # Groups
        self.deserialize_groups()

        deserialized_collection_set = self._load_collection_set()
        # If collection set exists, deserialize nothing else
        if not CollectionSet.objects.filter(collection_set_id=deserialized_collection_set.object.collection_set_id).exists():
            log.debug("Collection set does not exist, so proceeding with deserialization")

            # Save the collection set
            deserialized_collection_set.save()

            # Historical collection sets
            self._deserialize(self.historical_collections_set_record_filepath)

        else:
            log.warning("Not loading from %s since collection set already exists", self.collection_set_path)

    def _load_collection_set(self):
        return self._deserialize_iter(self.collections_set_record_filepath).next()

    def deserialize_groups(self):
        for deserialized_group in self._deserialize_iter(self.group_record_filepath):
            if not Group.objects.filter(name=deserialized_group.object.name).exists():
                log.debug("Saving %s", deserialized_group.object.name)
                deserialized_group.save()
            else:
                log.debug("%s already exists", deserialized_group.object.name)

    def _deserialize(self, filepath):
        for deserialized_obj in self._deserialize_iter(filepath):
            deserialized_obj.save()

    def _deserialize_iter(self, filepath):
        log.debug("Deserializing %s", filepath)
        with codecs.open(filepath, "r") as f:
            for deserialized_obj in serializers.deserialize("json", f):
                yield deserialized_obj
