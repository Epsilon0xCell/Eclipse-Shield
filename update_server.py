import xml.etree.ElementTree as ET

def generate_update_xml(version, update_url):
    # I write update.xml into the working directory, not next to this
    # script. I run this file from the repo root, which is where the app
    # serves update.xml from, and running it anywhere else leaves the
    # file in the wrong place with no error.
    root = ET.Element("gupdate", xmlns="http://www.google.com/update2/response", protocol="2.0")
    app = ET.SubElement(root, "app", appid="your-extension-id")
    updatecheck = ET.SubElement(app, "updatecheck", codebase=update_url, version=version)

    tree = ET.ElementTree(root)
    tree.write("update.xml", encoding="utf-8", xml_declaration=True)

# The id and the URL below are placeholders from the template this file
# started as. Until I replace them with the real extension id and the
# real hosted file, the XML this writes points at nothing. It is a
# generator waiting on its inputs, not a live update channel.
if __name__ == "__main__":
    version = "1.0.0"
    update_url = "https://your-github-username.github.io/your-repo-name/extension.crx"
    generate_update_xml(version, update_url)
