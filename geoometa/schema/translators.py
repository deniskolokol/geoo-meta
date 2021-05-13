# -*- coding: utf-8 -*-

"""
This module contains classes for translating original records from
Gazetteer to the format of ES index.
"""

from __future__ import absolute_import

from genery.utils import RecordDict

from core.exceptions import FieldError, WrongValueError


# Mapping of fields from Whosonfirst data to the Place
# document in index.
# Warning: only those fields are mentioned here that match
# directly, not requiring any additional logic.
FIELD_MAP = {
    "wof:name": "name",
    "geom:area": "area",
    "geom:area_square_m": "area_square_m",
    "iso:country": "iso_country",
    "wof:country": "country",
    "wof:geomhash": "geomhash",
    "wof:belongsto": "belongsto",
    "wof:hierarchy": "hierarchy",
    "wof:parent_id": "parent_id",
    "wof:placetype": "placetype",
    "wof:tags": "tags"
    }


class PlaceTranslator(RecordDict):
    def __init__(self, **feature):
        try:
            obj = feature["properties"]
            id_ = feature["id"]
        except KeyError:
            raise FieldError("Both `properties` and `id` must be present!")
        else:
            type_ = feature.get("type", "")
            if type_.lower() != "feature":
                type_ = "<{}>".format(type_.lower()) or "<empty>"
                raise WrongValueError(
                    "Only type `Feature` is allowed (found {})!"\
                    .format(type_))
        obj.update(meta={"id": id_})
        super().__init__(**obj)

    def translate(self):
        obj = {}
        for src, trg in FIELD_MAP.items():
            try:
                obj[trg] = getattr(self, src)
            except (KeyError, AttributeError):
                obj[trg] = None

        obj.update(self.extract_names)

    def extract_names(self):
        """
        Preserve lang-specific names, but pack it
        in a separate field.
        """
        names = []
        names_lang = {}
        for field, val in self.items():
            if not isinstance(val, list):
                val = [val]

            # General names.
            if field.endswith(":name"):
                names.extend(val)

            # Lang-specific names.
            if field.startswith("name:") and (
                    field.endswith("_preferred") or
                    field.endswith("_variant")
                ):

                # Fill in general container (for search).
                names.extend(val)

                # Fill in language specific container
                try:
                    _, lang = field.split(":")
                    lang = lang.split("_")[0]
                except Exception:
                    continue

                else:
                    # If target language cannot be found here,
                    # fieldname is created from the first two
                    # symbols ("kor" -> "ko").
                    if lang in LANG_MAP:
                        lang = LANG_MAP[lang]
                    else:
                        lang = lang[:2]

                # NB: val is a list.
                try:
                    names_lang[lang].extend(val)
                except KeyError:
                    names_lang[lang] = val
                except Exception:
                    continue

        # Names can be spelled similarly in different langs.
        names = distinct_elements(flatten_list(names))
        return {
            "names": names,
            "names_lang": names_lang
            }
