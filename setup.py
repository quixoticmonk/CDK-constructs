import setuptools

setuptools.setup(
    name="test_git",
    version="0.0.1",

    author="Manu Chandrasekhar",

    package_dir={"": "lib"},
    packages=setuptools.find_packages(where="lib"),
)
