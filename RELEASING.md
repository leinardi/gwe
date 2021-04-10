# Releasing

1. `flatpak run org.freedesktop.appstream-glib validate data/com.leinardi.gwe.appdata.xml`
2. Bump the `APP_VERSION` property in `gwe/conf.py` based on Major.Minor.Patch naming scheme
3. Update `data/com.leinardi.gwe.appdata.xml` for the impending release.
4. Run `./build.sh` to update the CHANGELOG.md
5. Update the `README.md` with the new changes (if necessary).
6. `git commit -am "Prepare for release X.Y.Z"` (where X.Y.Z is the version you set in step 1)
7. `flatpak uninstall com.leinardi.gwe --assumeyes; ./build.sh --flatpak-local --flatpak-install --flatpak-bundle && flatpak run com.leinardi.gwe --debug`
8. Tag version `X.Y.Z` (`git tag -s X.Y.Z`) (where X.Y.Z is the version you set in step 1)
9. Update tag and SHA in `flatpak/com.leinardi.gwe.json`
10. `git push --follow-tags` 
11. Trigger Flathub build bot `cd flatpak && git commit -am "Release X.Y.Z" && git push` (where X.Y.Z is the version you set in step 1)
12. Make a PR to the Flathub repository master, test the build and, if OK, merge the PR (https://github.com/flathub/com.leinardi.gwe)
13. `git commit -am "Release X.X.X" && git push` (where X.Y.Z is the version you set in step 1)
14. Create a PR from [master](../../tree/master) to [release](../../tree/release)
15. Using the "Edit release note" button, add the changelog items to the newly created tag on GitLab to make it an official Release (https://gitlab.com/leinardi/gkraken/-/tags)
16. Announce the new release on the App's Discord channel