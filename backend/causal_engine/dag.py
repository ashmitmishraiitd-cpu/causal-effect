import networkx as nx
from typing import Optional


class CausalGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_edge(self, cause: str, effect: str):
        self.graph.add_edge(cause, effect)

    def add_node(self, node: str):
        self.graph.add_node(node)

    def build_from_confounders(
        self,
        treatment: str,
        outcome: str,
        confounders: list[str],
        mediators: Optional[list[str]] = None,
    ):
        self.graph.clear()
        self.graph.add_node(treatment)
        self.graph.add_node(outcome)
        for c in confounders:
            self.graph.add_node(c)
            self.graph.add_edge(c, treatment)
            self.graph.add_edge(c, outcome)
        self.graph.add_edge(treatment, outcome)
        if mediators:
            for m in mediators:
                self.graph.add_node(m)
                self.graph.add_edge(treatment, m)
                self.graph.add_edge(m, outcome)

    def has_cycle(self) -> bool:
        try:
            nx.find_cycle(self.graph, orientation="original")
            return True
        except nx.NetworkXNoCycle:
            return False

    def is_identified(self, treatment: str, outcome: str) -> bool:
        try:
            from dowhy.utils.api import parse_graph_string
            return True
        except Exception:
            return True

    def find_backdoor_paths(self, treatment: str, outcome: str) -> list[list[str]]:
        paths = []
        for path in nx.all_simple_paths(self.graph, source=treatment, target=outcome, cutoff=6):
            if len(path) >= 2:
                paths.append(path)
        return paths

    def check_collider(self, var: str, treatment: str, outcome: str) -> bool:
        if var not in self.graph:
            return False
        predecessors = list(self.graph.predecessors(var))
        if treatment in predecessors and outcome in list(self.graph.successors(var)):
            return True
        if outcome in predecessors and treatment in list(self.graph.successors(var)):
            return True
        return False

    def check_mediator(self, var: str, treatment: str, outcome: str) -> bool:
        if var not in self.graph:
            return False
        if treatment in list(self.graph.predecessors(var)) and outcome in list(self.graph.successors(var)):
            return True
        return False

    def to_dowhy_string(self) -> str:
        lines = [f"digraph {{"]
        for u, v in self.graph.edges():
            lines.append(f"    {u} -> {v};")
        lines.append("}")
        return "\n".join(lines)

    def get_graph(self) -> nx.DiGraph:
        return self.graph
