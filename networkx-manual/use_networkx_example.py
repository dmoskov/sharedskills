#!/usr/bin/env python3
"""
Example of using NetworkX without pip installation.
This script shows how to import NetworkX directly from source.
"""

import sys
import os

# Add NetworkX to Python path programmatically
script_dir = os.path.dirname(os.path.abspath(__file__))
networkx_path = os.path.join(script_dir, 'networkx')
sys.path.insert(0, networkx_path)

# Now you can import and use NetworkX normally
import networkx as nx

# Example: Create and analyze a small social network
def create_social_network():
    """Create a simple social network graph"""
    G = nx.Graph()
    
    # Add nodes (people)
    people = ['Alice', 'Bob', 'Charlie', 'David', 'Eve']
    G.add_nodes_from(people)
    
    # Add edges (friendships)
    friendships = [
        ('Alice', 'Bob'),
        ('Alice', 'Charlie'),
        ('Bob', 'Charlie'),
        ('Bob', 'David'),
        ('Charlie', 'David'),
        ('David', 'Eve')
    ]
    G.add_edges_from(friendships)
    
    return G

# Create the network
network = create_social_network()

# Analyze the network
print("Social Network Analysis")
print("=" * 40)
print(f"Number of people: {network.number_of_nodes()}")
print(f"Number of friendships: {network.number_of_edges()}")
print(f"\nDegree of each person (number of friends):")
for person, degree in network.degree():
    print(f"  {person}: {degree} friends")

# Find shortest path
print(f"\nShortest path from Alice to Eve:")
path = nx.shortest_path(network, 'Alice', 'Eve')
print(f"  {' -> '.join(path)}")
print(f"  Distance: {len(path) - 1} hops")

# Check if graph is connected
print(f"\nIs everyone connected? {nx.is_connected(network)}")

# Find the most connected person
degrees = dict(network.degree())
most_connected = max(degrees, key=degrees.get)
print(f"Most connected person: {most_connected} with {degrees[most_connected]} friends")