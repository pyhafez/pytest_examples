"""Load our teaching plugin explicitly; installing the package has no global effects."""

pytest_plugins = ["pytest_power.pytest_plugin", "pytester"]
