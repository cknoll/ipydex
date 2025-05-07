# This file enables the ipydex excepthook together with pytest.
# The custom excepthook can be activated by `activate_ips_on_exception()`
# in your test-file.

# To prevent unwanted dependencies the custom excepthook is only active if a
# special environment variable is "True". Use the following command for this:
#
# export PYTEST_IPS=True


import os

if os.getenv("PYTEST_IPS") == "True":
    import ipydex

    # This function is just an optional reminder
    def pytest_runtest_setup(item):
        pass
        # print("This invocation of pytest is customized")

    def pytest_exception_interact(node, call, report):
        ipydex.ips_excepthook(call.excinfo.type, call.excinfo.value, call.excinfo.tb, leave_ut=True)
