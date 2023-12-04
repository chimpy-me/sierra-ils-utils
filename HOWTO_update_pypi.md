
# Updating Your Python Project on PyPI

Updating your Python project on PyPI involves several key steps. Here's a step-by-step guide to help you through the process.

## Steps to Update

1. **Update Your Project:**
   - Make necessary changes to your project.
   - Update the version number in `setup.py` or `pyproject.toml`.

2. **Update `README` and Documentation:**
   - Ensure all documentation is current with your changes.

3. **Update Dependencies:**
   - Update the dependency list if you have new or updated dependencies.

4. **Run Tests:**
   - Run your project's tests to ensure everything works correctly.

5. **Build the Distribution Files:**
   - Use `python setup.py sdist bdist_wheel` to create distribution files.

6. **Upload to PyPI:**
   - Use `twine upload dist/*` to upload the files to PyPI.

7. **Verify the Upload:**
   - Check your project page on PyPI and test installation using `pip install`.

8. **Tag Your Release:**
   - Tag the release in your version control system, e.g., `git tag -a v1.2.3 -m "version 1.2.3"`.

9. **Announce Your Release:**
   - Notify your user base of the new release, if applicable.

## Notes

- Ensure you have the latest versions of `setuptools`, `wheel`, and `twine`.
- Follow the Python Packaging Authority (PyPA) guidelines for best practices.
