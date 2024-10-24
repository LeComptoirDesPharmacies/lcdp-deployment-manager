from setuptools import setup

setup(
    name='lcdp_deployment_manager',  # How you named your package folder
    packages=['lcdp_deployment_manager'],  # Chose the same as "name"
    version='1.2.5rc3985-2',  # Start with a small number and increase it with every change you make
    license='MIT',  # Chose a license from here: https://help.github.com/articles/licensing-a-repository
    # description: Give a short description about your library
    long_description_content_type="text/plain",
    description='High level utilities to get/set AWS infrastructure items on prod',
    long_description='High level utilities to get/set AWS infrastructure items on prod',
    author='Géry THRASIBULE',  # Author's name
    author_email='g.thrasibule@lecomptoirdespharmacies.fr',  # Author's E-Mail
    # url: Provide either the link to your github or to your website
    url='https://github.com/LeComptoirDesPharmacies/lcdp-deployment-manager',
    # download_url: Up the version (use the same version as in "version")
    download_url='https://github.com/LeComptoirDesPharmacies/lcdp-deployment-manager/archive/1.2.5rc3985-2.tar.gz',
    keywords=['AWS', 'Python', 'Deployment'],  # Keywords that define your package best
    classifiers=[
        'Development Status :: 3 - Alpha',
        # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',  # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',  # Pick a license
        'Programming Language :: Python :: 3',  # Specify which python versions that you want to support
    ],
    install_requires=['boto3'],  # list your package's dependencies
)
