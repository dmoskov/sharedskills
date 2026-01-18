#!/usr/bin/env python3
import sys
import os

# Add the networkx directory to Python path
networkx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'networkx')
sys.path.insert(0, networkx_path)

# Now import networkx
import networkx as nx

# Test basic functionality
print(f"NetworkX version: {nx.__version__}")
print(f"NetworkX location: {nx.__file__}")

# Create a simple graph to test it works
G = nx.Graph()
G.add_edge('A', 'B')
G.add_edge('B', 'C')
G.add_edge('C', 'A')

print(f"\nCreated a graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
print(f"Nodes: {list(G.nodes())}")
print(f"Edges: {list(G.edges())}")