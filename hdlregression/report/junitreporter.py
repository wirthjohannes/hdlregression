#
# Copyright (c) 2022 by HDLRegression Authors.  All rights reserved.
# Licensed under the MIT License; you may not use this file except in compliance with the License.
# You may obtain a copy of the License at https://opensource.org/licenses/MIT.
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
# HDLRegression AND ANY PART THEREOF ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH UVVM OR THE USE OR OTHER DEALINGS IN HDLRegression.
#

from xml.etree import ElementTree as ET
from xml.dom import minidom
from .hdlreporter import HDLReporter
from ..run.hdltests import TestStatus

class JUNITReporter(HDLReporter):
    '''
    HDLReporter sub-class for documenting testcase run
    to a JUNIT XML file.
    '''

    def __init__(self, project=None, filename=None):
        super().__init__(project=project, filename=filename)

    def write_to_file(self) -> None:
        '''
        Writes regression run result to file in XML format.
        '''

        passing_tests, fail_tests, not_run_tests = self.project.get_results()

        root = ET.Element("testsuite")
        root.attrib["name"] = "testsuite"
        root.attrib["errors"] = "0"
        root.attrib["timestamp"] = str(self._time_of_run())
        root.attrib["time"] = f"{(self._time_of_sim()/1000):.1f}"
        root.attrib["failures"] = str(len(fail_tests))
        root.attrib["skipped"] = str(len(not_run_tests))
        root.attrib["tests"] = str(len(passing_tests)+len(fail_tests)+len(not_run_tests))

        for tc in self.project.runner.get_test_list():
            test = ET.Element("testcase")
            test.attrib["name"] = tc.get_testcase_name()
            test.attrib["file"] = "test/" + tc.get_testcase_name() + ".bsv"
            test.attrib["time"] = f"{(tc.get_elapsed_time()/1000):.1f}"

            system_out = ET.SubElement(test, "system-out")
            system_out.text = tc.get_output()

            if tc.get_status() == TestStatus.FAIL:
                failure = ET.SubElement(test, "failure")
                failure.attrib["message"] = "Failed"

            elif tc.get_status() == TestStatus.NOT_RUN:
                skipped = ET.SubElement(test, "skipped")
                skipped.attrib["message"] = "Skipped"

            root.append(test)
        # Do not create report if no test was run
        if self._check_test_was_run():
            # Convert the XML tree to a prettified string
            xml_string = ET.tostring(root, encoding="unicode", method="xml")
            formatted_xml = minidom.parseString(xml_string).toprettyxml(indent="    ")

            # Write the formatted XML string to file
            with open(self.get_full_filename(), 'w') as lf:
                lf.write(formatted_xml)
