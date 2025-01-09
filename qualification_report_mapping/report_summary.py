#!/usr/bin/python

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License

"""Loads the report summary mapping from a JSON file.

This module parses the `report_summary.json` file and stores the mapping
in the `report_summary` variable.  The `parse_json` utility function
is used to perform the parsing.
"""


from utils import parse_json  # pylint: disable=E0401

report_summary = parse_json(
    "./qualification_report_mapping_json/report_summary.json")
