from distutils.core import setup
setup(
  name = 'lcdp_deployment_manager',         # How you named your package folder (MyLib)
  packages = ['lcdp_deployment_manager'],   # Chose the same as "name"
  version = '0.1',      # Start with a small number and increase it with every change you make
  license='MIT',        # Chose a license from here: https://help.github.com/articles/licensing-a-repository
  description = 'High level utilities to get/set AWS infrastructure items on prod',   # Give a short description about your library
  author = 'Géry THRASIBULE',                   # Type in your name
  author_email = 'g.thrasibule@lecomptoirdespharmacies.fr',      # Type in your E-Mail
  url = 'https://github.com/LeComptoirDesPharmacies/lcdp-deployment-manager',   # Provide either the link to your github or to your website
  download_url = 'https://github.com/ijennine/lcdp-deployment-manager/archive/v_01.tar.gz',    # I explain this later on
  keywords = ['AWS', 'Python', 'Deployment'],   # Keywords that define your package best
  #install_requires=[            # I get to this in a second
  #       'boto3'
  #   ],
  classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
  ],
)