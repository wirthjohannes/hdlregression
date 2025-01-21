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


import os

from .sim_runner import SimRunner, OutputFileError
from ..report.logger import Logger
from ..hdlregression_pkg import os_adjust_path
from ..scan.hdl_regex_pkg import RE_VIVADO_WARNING, RE_VIVADO_ERROR
import re
from threading import Thread
from queue import Queue

class BluesimRunner(SimRunner):

    SIMULATOR_NAME = "BLUESIM"

    def __init__(self, project):
        super().__init__(project)
        self.logger = Logger(name=__name__, project=project)
        self.project = project
        self.project.settings.result_check_str = "1234"
        self._compile_regex()

    def _compile_regex(self):
        # Setup regex
        super()._compile_regex()
        ID_BLUESIM_ERROR = r"\[ERROR\]"
        self.RE_BLUESIM_ERROR = re.compile(
            ID_BLUESIM_ERROR
        )
        ID_BLUESIM_WARNING = r"\[WARN\]"
        self.RE_BLUESIM_WARNING = re.compile(
            ID_BLUESIM_WARNING
        )
        ID_BLUESIM_SUCCESS = r"Finished test"
        self.RE_BLUESIM_SUCCESS = re.compile(
            ID_BLUESIM_SUCCESS
        )

    def _setup_ini(self) -> str:
        return None

    @classmethod
    def _is_simulator(cls, simulator) -> bool:
        return (simulator.upper() == cls.SIMULATOR_NAME)

    def _compile_library(self, library, force_compile=False) -> 'HDLLibrary':
        files = library.get_hdlfile_list()

        num_threads = self._get_number_of_threads()

        # create test queue for threads to operate with
        compile_queue = Queue()
        for file in files:
            compile_queue.put(file)

        def run_compile(compile_queue) -> bool:
            while not compile_queue.empty():
                # try:
                file = compile_queue.get()
                path = os.path.join(
                    self.project.settings.get_output_path(),
                    "library",
                    file.get_name().lower()
                )
                path = os_adjust_path(path)
                # Create library
                if not os.path.isdir(path):
                    self._run_cmd(command=["mkdir", path])
                output = os.path.join(path, "build.log")
                # Map library
                command = ["make", "BUILDDIR=" + path, "RUN_TEST="+file.get_name(), "NOCOLOR=1"]
                command += file.get_com_options()
                command += [path + "/out"]
                self._run_cmd(
                    command=command,
                    output_file=output,
                    suppressErrors=True
                )
                # finally:
                compile_queue.task_done()

        # run threads
        for _ in range(num_threads):
            thread = Thread(target=run_compile, args=(compile_queue,))
            thread.daemon = True
            thread.start()

        # wait for test queue to finish
        compile_queue.join()

        return library

    def _get_simulator_error_regex(self):
        return RE_VIVADO_ERROR

    def _get_simulator_warning_regex(self):
        return RE_VIVADO_WARNING

    def _get_netlist_call(self) -> str:
        return ''

    def _simulate(self, test, generic_call, module_call) -> bool:
        print('--->> starting sim')
        path = os.path.join(
            "..",
            "..",
            "library",
            test.get_testcase_name().lower()
        )
        path = os_adjust_path(path)
        command = ['bash', path + "/out"]
        output = os.path.join(test.get_test_path(), "run.log")
        output = os_adjust_path(output)
        success = self._run_cmd(command=command, test=test, path=test.get_test_path(), output_file=output, timeout=30*60)
        print('---->>> sim done')
        return success
    
    def prepare_test_modules_and_objects(self, re_run_tc_list):
        """
        Locate testbench modules and build test objects
        """
        self.testbuilder.build_tb_module_list()
        for tb in self.testbuilder.testbench_container.get():
            for tc in tb.get_testcase():
                test = self.testbuilder._get_test_object(tb=tb)
                test.set_tc(tc)
                self.testbuilder.tests_to_run_container.add(test)
        self.testbuilder.base_tests_container.add_element_from_list(
            self.testbuilder.tests_to_run_container.get()
        )
        self.testbuilder.build_list_of_tests_to_run_base(re_run_tc_list)

    def _get_descriptive_test_name(self, test, architecture_name, module_call):
        return module_call

    def _get_module_call(self, test, architecture_name):
        lib_name = test.get_library().get_name()
        return "{}.{}".format(lib_name, test.get_name())
    
    def _get_simulator_error_regex(self):
        return self.RE_BLUESIM_ERROR

    def _get_simulator_warning_regex(self):
        return self.RE_BLUESIM_WARNING

    def _is_user_selected_result_match(self, line):
        return re.search(self.RE_BLUESIM_SUCCESS, line)
