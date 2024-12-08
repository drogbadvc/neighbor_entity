import streamlit as st
import requests
import json
import pandas as pd
from st_table_words_icon import block_html

st.set_page_config(page_title="Neighbor Entity", layout="wide")

@st.cache_data
def load_languages(file_path='languages.json'):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            languages = json.load(f)
        return languages
    except FileNotFoundError:
        st.error("Le fichier des langues n'a pas été trouvé.")
        return []
    except json.JSONDecodeError:
        st.error("Erreur de décodage du fichier JSON des langues.")
        return []

LANGUAGES = load_languages()

def clean_keyword(kw):
    return kw.title().replace('_', ' ').replace('%20', ' ').strip()


def card(title, context):
    return f"""
        <div class ="card data-clusters">
            <div class ="card-body">
                <h5 class ="card-title">{title}</h5>
                {context}
            </div>      
        </div>"""


@st.cache_data(show_spinner=False)
def convert_df(data):
    df = pd.DataFrame(data, columns=["keywords"])

    return df.to_csv().encode('utf-8')


st.title("Neighbor Entity")


@st.cache_data()
def NeighGraph(lang, title, nPredLevels, nSuccLevels, reverseData=False):
    # Prepare the URL and parameters.
    url = "http://www.wikifier.org/get-neigh-graph"
    params = {
        "lang": lang,
        "title": title,
        "nPredLevels": nPredLevels,
        "nSuccLevels": nSuccLevels
    }

    # Use requests.Session() for connection reuse
    session = requests.Session()

    try:
        # Call the Wifelier and read the response.
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response_data = response.json()

        # Print the edges of the graph.
        nVertices = response_data.get("nVertices")
        if not nVertices:
            return False
        else:
            titles = response_data["titles"]
            data = runData(nVertices, response_data, titles, reverseData)

            return [data, titles]

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return st.error(f"Error: {e}")
    except requests.exceptions.Timeout:
        st.error("The request has expired. Please try again later.")
        return False
    except requests.exceptions.HTTPError as http_err:
        st.error(f"Error HTTP: {http_err}")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {e}")
        return False


def pushData(data, titleChildren, titleParent):
    if titleParent != clean_keyword(keyword_input):
        if len(data['children']) > 0:
            childrenItems = [index for index, item in enumerate(data['children']) if
                             'name' in item and item['name'] == titleParent]
            childrenIndex = childrenItems[0] if len(childrenItems) > 0 else -1
        else:
            childrenIndex = -1
        if childrenIndex == -1:
            data['children'].append({"children": [], "name": titleParent})

        children_names = list(map(lambda item: item['name'], data['children'][childrenIndex]['children']))
        if childrenIndex != -1 and titleChildren not in children_names and titleChildren != \
                titleParent:
            data['children'][childrenIndex]['children'].append({"name": titleChildren, "size": 2})
        # print("%s -> %s" % (titles[u], titles[v]))


def runData(nVertices, response, titles, reverseData=False):
    nEdges = 0
    data = {"name": clean_keyword(keyword_input), "children": [], "size": 1}
    for u in range(nVertices):
        for v in response["successors"][u]:
            if reverseData:
                pushData(data, titles[u], titles[v])
            else:
                pushData(data, titles[v], titles[u])
            nEdges += 1
    # nEdges == response["nEdges"]

    return data


def extract_names(dct: dict) -> list:
    names = [dct["name"]]
    children = dct.get("children", [])
    for child in children:
        names.extend(extract_names(child))
    return names


def extract_top_level_names(dct: dict) -> list:
    if not isinstance(dct, dict):
        return []
    names = []
    children = dct.get("children", [])
    for child in children:
        if isinstance(child, dict):
            names.append(child.get('name', ''))
    return names


if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# Interface utilisateur
col_lang, col_input = st.columns([1, 3])

with col_lang:
    language = st.selectbox(
        "Langue",
        options=LANGUAGES,
        format_func=lambda lang: lang["name"],
        index=0
    )

with col_input:
    keyword_input = st.text_input(
        "Entrez un texte ici :",
        value=st.session_state.input_text if "input_text" in st.session_state else ""
    )

if keyword_input:
    with st.spinner(''):
        keyword_name = keyword_input.title().strip()
        dataGraph = NeighGraph(language["code"], clean_keyword(keyword_name), 0, 1)
        if dataGraph:
            names_list = extract_names(dataGraph[0])
            parent_list = extract_top_level_names(dataGraph[0])
            if not dataGraph:
                st.error("This is empty, you are sure to have written a wikipedia entity 🚨")
            else:
                csv = convert_df(names_list)
                json_data = json.dumps(dataGraph)
                col3, col4 = st.columns([1, 3])
                with col3:
                    st.download_button(
                        label="Download data as CSV",
                        data=csv,
                        file_name=keyword_name + '.csv',
                        mime='text/csv',
                    )
                with col4:
                    st.download_button(
                        label="Download data as Json",
                        data=json_data,
                        file_name=keyword_name + '.json',
                        mime='application/json',
                    )
                col1, col2 = st.columns([1, 3])
                with col1:

                    data_word = block_html(names_list)

                    if data_word and data_word != st.session_state.input_text:
                        st.session_state.input_text = data_word
                        st.rerun()

                with col2:

                    tree_diagram_html = """
                    <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    path.link {
fill: none;
stroke: #ccc;
stroke-width: 2px;
}
svg {
width: 100%;
}
.card {
border: 1px #1b1e21;
box-shadow: 0 3px 10px rgba(62, 85, 120, .045);
margin-bottom: 25px;
border-radius: 4px;
position: relative;
display: -ms-flexbox;
display: flex;
-ms-flex-direction: column;
flex-direction: column;
min-width: 0;
word-wrap: break-word;
background-color: transparent;
background-clip: border-box;
}
</style>
</head>
<body>
<div class="card" id="tree-diagram"></div>
<script src="https://d3js.org/d3.v3.min.js"></script>
<script id="tree-data" type="application/json">PLACEHOLDER_DATA</script>

<script>
const treeDataElement = document.getElementById("tree-data");
const treeData = JSON.parse(treeDataElement.textContent);

 const colors = ["#CDB699", "#2C272E", "#325288", "#D96098", "#91C483", "#FF6464",
        "#cf5d85", "#617c65", "#47da78", "#716fb9", "#cf9e70", "#ababab",
        "#24A19C", "#30475E", "#7CD1B8", "#753188", "#9D84B7", "#F8485E"
    ]
 const color = d3.scale.ordinal().domain(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']).range(colors)

function drawTree(element, data) {

var tree = d3.layout.tree()
        .size([360, width / 2 - 160])
        .separation(function (a, b) {
            return (a.parent == b.parent ? 1 : 2) / a.depth;
        });

root = ''
root = data;
root.x0 = height / 2;
root.y0 = 0;


// ************** Generate the tree diagram	 *****************
    var margin = {top: 20, right: 120, bottom: 20, left: 120},
        width = 600 - margin.right - margin.left,
        height = 400 - margin.top - margin.bottom

    var i = 0,
        duration = 750,
        root;

    var tree = d3.layout.tree()
        .size([height, width])

    var diagonal = d3.svg.diagonal()
.projection(function(d) { return [d.y, d.x]; });

if(d3.select("#d3-tree")[0][0] === null) {
    var svg = d3.select("#tree-diagram").append("svg")
.attr("id", "d3-tree")
.attr("width", width + margin.right + margin.left)
.attr("height", height + margin.top + margin.bottom)
.append("g")
.attr("transform", "translate(" + margin.left + "," + margin.top + ")");
}else{
    d3.select("#d3-tree").style("display","block")
   var svg = d3.select("#d3-tree")
}



root.children.forEach(collapse)
update(root)

function collapse(d) {
    if (d.children) {
        d._children = d.children;
        d._children.forEach(collapse);
        d.children = null;
    }
}

d3.select(self.frameElement)

function update(source) {
var newHeight = Math.max(tree.nodes(root).reverse().length * 20, height);

d3.select("#tree-diagram svg#d3-tree")
.attr("width", width + margin.right + margin.left)
.attr("height", newHeight + margin.top + margin.bottom);

tree = d3.layout.tree().size([newHeight, width]);
// Compute the new tree layout.
var nodes = tree.nodes(root).reverse(),
  links = tree.links(nodes);

// Normalize for fixed-depth.
nodes.forEach(function(d) { d.y = d.depth * 180; })

// Update the nodes…
var node = svg.selectAll("g.node")
  .data(nodes, function(d) { return d.id || (d.id = ++i); })

// Enter any new nodes at the parent's previous position.
var nodeEnter = node.enter().append("g")
  .attr("class", "node")
  .attr("transform", function(d) {
if (isNaN(source.y0) || isNaN(source.x0)) {
    return "translate(0,0)"; // Fallback to a default value
}
return "translate(" + source.y0 + "," + source.x0 + ")";
})
  .on("click", click);

nodeEnter.append("circle")
  .attr("r", 1e-6)
  .attr("stroke", d => d.children ? null : "#fff")
  .style("fill", function (d) {
                return color(d.size)
            })
nodeEnter.append("text")
  .attr("x", function (d) {
return 15;
})
  .attr("dy", ".35em")
  .attr("text-anchor", function (d) {
return "start";
})
  .text(function(d) { return d.name; })
  .style("fill-opacity", 1e-6);

// Transition nodes to their new position.
var nodeUpdate = node.transition()
  .duration(duration)
  .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

nodeUpdate.select("circle")
  .attr("r", 4.5)
  .style("fill", function (d) {
                return color(d.size)
            })

nodeUpdate.select("text")
  .style("fill-opacity", 1);

// Transition exiting nodes to the parent's new position.
var nodeExit = node.exit().transition()
  .duration(duration)
  .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
  .remove();

nodeExit.select("circle")
  .attr("r", 1e-6);

nodeExit.select("text")
  .style("fill-opacity", 1e-6);

// Update the links…
var link = svg.selectAll("path.link")
  .data(links, function(d) { return d.target.id; });

// Enter any new links at the parent's previous position.
link.enter().insert("path", "g")
  .attr("class", "link")
  .attr("stroke-opacity", 0.6)
  .attr("stroke", "#999")
  .attr("d", function(d) {
var o = {x: source.x0, y: source.y0};
if (isNaN(o.x) || isNaN(o.y)) {
    return "M0,0L0,0"; // Fallback to a default diagonal
}
return diagonal({source: o, target: o});
})

// Transition links to their new position.
link.transition()
  .duration(duration)
  .attr("d", diagonal);

// Transition exiting nodes to the parent's new position.
link.exit().transition()
  .duration(duration)
  .attr("d", function(d) {
    var o = {x: source.x, y: source.y};
    return diagonal({source: o, target: o});
  })
  .remove();

// Stash the old positions for transition.
nodes.forEach(function(d) {
d.x0 = d.x;
d.y0 = d.y;
});
}


// Toggle children on click.
function click(d) {
if (d.children) {
d._children = d.children;
d.children = null;
} else {
d.children = d._children;
d._children = null;
}
update(d);
}
}


   document.addEventListener("DOMContentLoaded", function () {
    drawTree("#tree-diagram", treeData);
  });
</script>
</body>
</html>
"""

                    tree_data_str = json.dumps(dataGraph[0])
                    height = round(len(parent_list) * 20.5)
                    if height < 500:
                        height = 500

                    tree_diagram_html = tree_diagram_html.replace("PLACEHOLDER_DATA", tree_data_str)

                    st.components.v1.html(tree_diagram_html, height=height)
