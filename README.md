# lcdp-deployment-manager
High level utilities to get/set AWS infrastructure items on prod

#### Instructions to deploy this package to PyPI:
1. Prepare your code for deployment: remove code outside of your classes.

2. Add your classes to the `__init__.py` file as follows:

        from lcdp_deployment_manager.Filename1 import Classname1
        from lcdp_deployment_manager.Filename2 import Classname2
        
    > Warning: package users will only have access to the classes specified in this file.

3. Push your changes to Github:

    * https://github.com/LeComptoirDesPharmacies/lcdp-deployment-manager

4. Edit the setup.py file.
    > Instructions to edit this file are provided inside the script.

5. Create a link to download your source code using Github:
    
    a. Navigate to your repository.
    
    b. Click on the "releases" tab and "Create a new release".
    
    c. Define a tag version (preferably use the same version as in the `Setup.py` file).
    
    d. Add a release title and description and click on "publish release" (not necessary).
 
6. Install `setuptools`, `wheel` and `twine` and :

        python3 -m pip install --user --upgrade setuptools wheel twine
7. Run this command from the same directory where `setup.py` is located:

        python3 setup.py sdist bdist_wheel
8. Upload the distribution archive to PyPI:
*( Recommended: upload your package to "Test PyPI" first to make sure that your deployment will be successful)*

    * Run this command to upload your package to "Test PyPI":
    
            python3 -m twine upload --repository testpypi dist/*
        
    * Run this command to upload your package to PyPI's Main website:
    
            python3 -m twine upload dist/*

9. Test your deployment

    * From Test PyPI:
    
            python3 -m pip install --index-url https://test.pypi.org/simple/ lcdp-deployment-manager
            
    * From PyPI:
    
            python3 -m pip install lcdp-deployment-manager
            
10. For more information or if your deployment fails, check these links:
    * https://medium.com/@joel.barmettler/how-to-upload-your-python-package-to-pypi-65edc5fe9c56
    
    * https://packaging.python.org/tutorials/packaging-projects