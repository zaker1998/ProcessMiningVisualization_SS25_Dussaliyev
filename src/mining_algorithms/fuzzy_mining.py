from graphs.visualization.fuzzy_graph import FuzzyGraph
import numpy as np
from mining_algorithms.base_mining import BaseMining
from logger import get_logger


class FuzzyMining(BaseMining):

    def __init__(self, cases):
        from config import cluster_seperator

        self.cluster_seperator = cluster_seperator

        super().__init__(cases)
        self.logger = get_logger("FuzzyMining")
        self.minimum_correlation = None
        self.correlation_of_nodes = self.__create_correlation_dependency_matrix()
        self.significance_of_nodes = self.__calculate_significance()
        self.node_significance_matrix = self.__calculate_node_significance_matrix(
            self.significance_of_nodes
        )
        self.clustered_nodes = None
        self.sign_dict = None

        self.significance = 0.0
        self.correlation = 0.0
        self.edge_cutoff = 0.0
        self.utility_ratio = 0.0
        """
        stores the cluster_id as an value and the nodes int the cluster as the key. The node ids are separated by a the cluster seperator
        """
        self.cluster_id_mapping = None

    def create_graph_with_graphviz(
        self, significance, correlation, edge_cutoff, utility_ratio
    ):
        self.significance = significance
        self.correlation = correlation
        self.edge_cutoff = edge_cutoff
        self.utility_ratio = utility_ratio
        self.cluster_id_mapping = {}

        self.minimum_correlation = correlation
        # self.correlation_of_nodes = self.__calculate_correlation_dependency_matrix(correlation)
        self.graph = FuzzyGraph()

        self.logger.debug("Significance: " + str(significance))
        self.logger.debug("Succession: " + "\n" + str(self.succession_matrix))
        # 1 Rule remove less significant and less correlated nodes
        self.corr_after_first_rule, self.sign_after_first_rule = (
            self.__calculate_first_rule(
                self.events,
                self.correlation_of_nodes,
                self.node_significance_matrix,
                significance,
            )
        )

        # Edge Filtering

        # 1-first rule of edge filtering - multiply each correlation and significance node with utility ration
        # util= ur*(correlation+significance)
        # returns  removed_indices = [[0 4], [1 2]]
        list_of_filtered_edges = self.__find_removed_edges_after_edge_filtering(
            utility_ratio,
            edge_cutoff,
            self.sign_after_first_rule,
            self.corr_after_first_rule,
        )
        # 2-second rule of edge filtering - then find normalised util
        # NU = (util-MinU)/(MaxU-MinU)
        # 3-third rule of edge filtering - then check which values are greater than cutoff value
        # if >= | > edge_cutoff setvalue of normalised util (NU) else -1 or check how to do it

        # returns a list of significant nodes e.g ['a', 'b', 'd'], not relevant nodes are not included
        nodes_after_first_rule = self.__calculate_significant_nodes(
            self.corr_after_first_rule
        )
        self.logger.debug(
            "sign_after_first_rule-->" + "\n" + str(self.sign_after_first_rule)
        )
        self.logger.debug(
            "corr_after_first_rule-->" + "\n" + str(self.corr_after_first_rule)
        )

        # 2 Rule less significant but highly correlated nodes are going to be clustered
        clustered_nodes_after_sec_rule = self.__calculate_clustered_nodes(
            nodes_after_first_rule,
            self.corr_after_first_rule,
            self.sign_after_first_rule,
            significance,
        )
        self.logger.debug("Clustered nodes: " + str(clustered_nodes_after_sec_rule))
        self.list_of_clustered_nodes = self.__convert_clustered_nodes_to_list(
            clustered_nodes_after_sec_rule
        )
        self.logger.debug(self.list_of_clustered_nodes)

        # significance after clustering
        sign_after_sec_rule = self.__update_significance_matrix(
            self.sign_after_first_rule, clustered_nodes_after_sec_rule
        )
        self.logger.debug(sign_after_sec_rule)
        self.sign_dict = self.__get_significance_dict_after_clustering(
            sign_after_sec_rule
        )
        # print("avg_Significance after clustering: " + str(self.sign_dict))

        # print clustered nodes
        self.__add_clustered_nodes_to_graph(
            self.graph, clustered_nodes_after_sec_rule, self.sign_dict
        )
        # normal nodes
        # normal_nodes_after_sec_rule = self.__calculate_normal_nodes()
        # what is already clustered is not a normal node
        self.__add_normal_nodes_to_graph(
            self.graph, nodes_after_first_rule, self.list_of_clustered_nodes
        )

        list_of_filtered_edges_as_node = self.__get_as_node_removed_indices(
            list_of_filtered_edges
        )

        self.__add_edges_to_graph(
            self.graph, clustered_nodes_after_sec_rule, list_of_filtered_edges_as_node
        )

        # add start and end nodes
        self.graph.add_start_node()
        self.graph.add_end_node()

        # add starting and ending edges from the log, only consider nodes which were not removed from the graph
        # if nodes are merged to cluster, get the cluster id

        start_nodes = set(
            map(
                lambda node: self.get_node_id(node),
                self.start_nodes.intersection(nodes_after_first_rule),
            )
        )
        end_nodes = set(
            map(
                lambda node: self.get_node_id(node),
                self.end_nodes.intersection(nodes_after_first_rule),
            )
        )

        self.logger.debug("Start nodes: " + str(start_nodes))
        self.logger.debug("End nodes: " + str(end_nodes))

        # can cause exception needs fix, for some reason there can be a node which is not in the graph, needs to be checked
        self.graph.add_starting_edges(start_nodes)
        self.graph.add_ending_edges(end_nodes)

        nodes = self.graph.get_node_ids()
        nodes = set(nodes) - set(["Start", "End"])

        # nodes with no incoming edges conected to start node
        for target in nodes:
            if self.graph.contains_edge("Start", target):
                continue
            is_start_node = True
            for source in nodes:
                if target == source:
                    continue
                if self.graph.contains_edge(source, target):
                    is_start_node = False
                    break
            if is_start_node:
                self.graph.add_starting_edges([target])

        # nodes with no outgoing edges conected to end node
        for source in nodes:
            if self.graph.contains_edge(source, "End"):
                continue
            is_end_node = True
            for target in nodes:
                if target == source:
                    continue
                if self.graph.contains_edge(source, target):
                    is_end_node = False
                    break
            if is_end_node:
                self.graph.add_ending_edges([source])

    def get_node_id(self, node):
        for key, value in self.cluster_id_mapping.items():
            if node in key:
                return value
        return node

    def __get_as_node_removed_indices(self, list_of_filtered_edges):
        removed_nodes = []
        for i, j in list_of_filtered_edges:
            removed_nodes.append([self.events[i], self.events[j]])
        return removed_nodes

    def __find_min_and_max_util_value(self, array):
        max_values = {}
        min_values = {}
        for i in range(array.shape[1]):
            column_values = array[:, i]
            non_zero_values = column_values[column_values != 0]

            column_max = np.max(column_values)
            if len(non_zero_values) > 0:
                column_min = np.min(non_zero_values)
            else:
                column_min = np.inf

            max_values[self.events[i]] = column_max
            min_values[self.events[i]] = column_min
        self.logger.debug("Maxx------: " + str(max_values))
        self.logger.debug("Minn------: " + str(min_values))
        return min_values, max_values

    def __find_removed_edges_after_edge_filtering(
        self, utility_ratio, edge_cutoff, sign_after_first_rule, corr_after_first_rule
    ):

        util_matrix = np.zeros((len(self.events), len(self.events)))

        # if edge cutoff is 0.0, no edge filtering will be done
        if edge_cutoff == 0.0:
            return []

        # just node-node will be checked
        for i in range(len(self.events)):
            # min_values, max_values = self.__find_min_and_max_util_value(util_matrix)
            for j in range(len(self.events)):
                # self loop will not be considered
                if i == j:
                    continue
                # if one of them is clustered continue
                # if self.events[i] in clustered_nodes_list or self.events[j] in clustered_nodes_list:
                #    continue
                # check if removes by Rule 3 low sign and low correlation
                # when removed correlation and significance of node will be -1
                if (
                    sign_after_first_rule[i][j] == -1
                    or corr_after_first_rule[i][j] == -1
                ):
                    continue

                # if not clustered and not removed check for edge filtering
                # why is this done?
                val = np.round(
                    sign_after_first_rule[i][j] * utility_ratio
                    + (1 - utility_ratio) * corr_after_first_rule[i][j],
                    2,
                )
                self.logger.debug(
                    "calculating util matriX "
                    + str(self.events[i])
                    + " -> "
                    + str(self.events[j])
                    + " value "
                    + str(val)
                )
                self.logger.debug(
                    "sign[i][j]= "
                    + str(sign_after_first_rule[i][j])
                    + " corr[j][i]= "
                    + str(corr_after_first_rule[i][j])
                    + " value "
                    + str(val)
                )
                util_matrix[i][j] = np.round(
                    sign_after_first_rule[i][j] * utility_ratio
                    + (1 - utility_ratio) * corr_after_first_rule[i][j],
                    2,
                )

            # find minU and maxU for each column

        minU, maxU = self.__find_min_and_max_util_value(util_matrix)

        self.logger.debug("111-printing utility ratio value \n" + str(utility_ratio))
        self.logger.debug("111-printing significance \n" + str(sign_after_first_rule))

        self.logger.debug("111-printing correlation \n" + str(corr_after_first_rule))

        self.logger.debug("Util Matrix-----> \n" + str(util_matrix))

        self.logger.debug("calculate normalised util. ")

        normalised_util_matrix = self.__calculate_normalised_util(
            util_matrix, edge_cutoff, minU, maxU, utility_ratio, corr_after_first_rule
        )
        removed_indices = []
        if not np.all(normalised_util_matrix == 0):
            removed_indices = np.argwhere(
                (corr_after_first_rule > 0.0) & (normalised_util_matrix == 0.0)
            )
        self.logger.debug("removed_indices = \n" + str(removed_indices))
        return removed_indices

    def __calculate_normalised_util(
        self, util_matrix, edge_cutoff, minU, maxU, utility_ratio, corr_after_first_rule
    ):
        normalised_matrix = np.zeros((len(self.events), len(self.events)))

        for i in range(len(self.events)):
            if edge_cutoff == 0 and utility_ratio == 0:
                break
            for j in range(len(self.events)):
                if i == j:
                    continue
                util_value = util_matrix[i][j]
                min_val = minU[self.events[j]]
                max_val = maxU[self.events[j]]

                numerator = util_value - min_val
                denominator = max_val - min_val

                # divide by 0 or 0 divided by a number will be assigned with 0
                if numerator == 0 or denominator == 0:
                    new_val = 0.0
                else:
                    new_val = np.round((numerator / denominator), 2)

                if (
                    not np.isnan(new_val)
                    and new_val >= edge_cutoff
                    and new_val > 0.0
                    and corr_after_first_rule[i][j] > 0
                ):
                    normalised_matrix[i][j] = new_val
                else:
                    normalised_matrix[i][j] = 0.0

        self.logger.debug("normalised_matrix = \n" + str(normalised_matrix))
        return normalised_matrix

    def __add_edges_to_graph_for_each_method(
        self, edges, graph, node_to_node_case, list_of_filtered_edges
    ):
        edge_thickness = 0.1
        for pair, value in edges.items():
            current_cluster = pair[0]
            next_cluster = pair[1]
            if node_to_node_case:
                if [current_cluster, next_cluster] in list_of_filtered_edges:
                    continue

                self.graph.create_edge(
                    current_cluster, next_cluster, edge_thickness, value
                )
            else:
                if current_cluster in self.cluster_id_mapping:
                    current_cluster = self.cluster_id_mapping.get(current_cluster)

                if next_cluster in self.cluster_id_mapping:
                    next_cluster = self.cluster_id_mapping.get(next_cluster)

                self.graph.create_edge(
                    current_cluster, next_cluster, edge_thickness, value, "red"
                )

    def __add_edges_to_graph(
        self, graph, clustered_nodes_after_sec_rule, list_of_filtered_edges
    ):
        (
            node_to_cluster_edge,
            cluster_to_node_edge,
            cluster_to_cluster_edge,
            node_to_node_edge,
        ) = self.__calculate_avg_correlation_for_clustered_nodes(
            self.corr_after_first_rule, clustered_nodes_after_sec_rule
        )

        self.__add_edges_to_graph_for_each_method(
            node_to_cluster_edge, self.graph, False, list_of_filtered_edges
        )
        self.__add_edges_to_graph_for_each_method(
            cluster_to_node_edge, self.graph, False, list_of_filtered_edges
        )
        self.__add_edges_to_graph_for_each_method(
            cluster_to_cluster_edge, self.graph, False, list_of_filtered_edges
        )
        self.__add_edges_to_graph_for_each_method(
            node_to_node_edge, self.graph, True, list_of_filtered_edges
        )

    def __calculate_avg_correlation_for_clustered_nodes(
        self, correlation_after_first_rule, clustered_nodes
    ):
        ret_node_to_cluster_edge = {}
        ret_cluster_to_node_edge = {}
        ret_cluster_to_cluster_edge = {}
        ret_node_to_node_edge = {}

        ret_node_to_cluster_edge_counter = {}
        ret_cluster_to_node_edge_counter = {}
        ret_cluster_to_cluster_edge_counter = {}

        # for cluster -> node, cluster -> cluster
        for i in range(len(self.events)):
            for j in range(len(self.events)):
                # self loops will be removed
                if self.events[i] == self.events[j]:
                    continue
                # current_cluster --> node
                if (
                    self.events[i] in self.list_of_clustered_nodes
                    and self.events[j] not in self.list_of_clustered_nodes
                    and correlation_after_first_rule[i][j] != -1
                    and correlation_after_first_rule[i][j] > 0
                ):
                    current_cluster = self.__get_cluster_where_node(
                        self.events[i], clustered_nodes
                    )
                    pair = (current_cluster, self.events[j])
                    if pair in ret_cluster_to_node_edge:
                        ret_cluster_to_node_edge[pair] += correlation_after_first_rule[
                            i
                        ][j]
                        ret_cluster_to_node_edge_counter[pair] += 1
                    else:
                        ret_cluster_to_node_edge[pair] = correlation_after_first_rule[
                            i
                        ][j]
                        ret_cluster_to_node_edge_counter[pair] = 1
                # current_cluster --> cluster
                elif (
                    self.events[i] in self.list_of_clustered_nodes
                    and self.events[j] in self.list_of_clustered_nodes
                    and self.events[j]
                    and correlation_after_first_rule[i][j] > 0
                ):
                    current_cluster = self.__get_cluster_where_node(
                        self.events[i], clustered_nodes
                    )
                    next_cluster = self.__get_cluster_where_node(
                        self.events[j], clustered_nodes
                    )
                    # not in same cluster
                    if current_cluster == next_cluster:
                        continue
                    pair = (current_cluster, next_cluster)
                    if pair in ret_cluster_to_cluster_edge:
                        ret_cluster_to_cluster_edge[
                            pair
                        ] += correlation_after_first_rule[i][j]
                        ret_cluster_to_cluster_edge_counter[pair] += 1
                    else:
                        ret_cluster_to_cluster_edge[pair] = (
                            correlation_after_first_rule[i][j]
                        )
                        ret_cluster_to_cluster_edge_counter[pair] = 1
                # node --> current_cluster
                elif (
                    self.events[i] not in self.list_of_clustered_nodes
                    and self.events[j] in self.list_of_clustered_nodes
                    and correlation_after_first_rule[i][j] != -1
                    and correlation_after_first_rule[i][j] > 0
                ):
                    next_cluster = self.__get_cluster_where_node(
                        self.events[j], clustered_nodes
                    )
                    pair = (self.events[i], next_cluster)
                    if pair in ret_node_to_cluster_edge:
                        ret_node_to_cluster_edge[pair] += correlation_after_first_rule[
                            i
                        ][j]
                        ret_node_to_cluster_edge_counter[pair] += 1
                    else:
                        ret_node_to_cluster_edge[pair] = correlation_after_first_rule[
                            i
                        ][j]
                        ret_node_to_cluster_edge_counter[pair] = 1
                # node ---> node
                elif (
                    self.events[i] not in self.list_of_clustered_nodes
                    and self.events[j] not in self.list_of_clustered_nodes
                    and correlation_after_first_rule[i][j] != -1
                    and correlation_after_first_rule[i][j] > 0
                ):
                    pair = (self.events[i], self.events[j])
                    if pair in ret_node_to_node_edge:
                        ret_node_to_node_edge[pair] += correlation_after_first_rule[i][
                            j
                        ]
                    else:
                        ret_node_to_node_edge[pair] = correlation_after_first_rule[i][j]

        self.logger.debug("node_to_cluster: " + str(ret_node_to_cluster_edge))
        self.logger.debug("cluster_to_node: " + str(ret_cluster_to_node_edge))
        self.logger.debug("cluster_to_cluster: " + str(ret_cluster_to_cluster_edge))
        self.logger.debug("node_to_node: " + str(ret_node_to_node_edge))

        self.logger.debug("node_to_cluster: " + str(ret_node_to_cluster_edge_counter))
        self.logger.debug("cluster_to_node: " + str(ret_cluster_to_node_edge_counter))
        self.logger.debug(
            "cluster_to_cluster: " + str(ret_cluster_to_cluster_edge_counter)
        )

        node_to_cluster_avg = self.__calculate_avg(
            ret_node_to_cluster_edge, ret_node_to_cluster_edge_counter
        )
        cluster_to_node_avg = self.__calculate_avg(
            ret_cluster_to_node_edge, ret_cluster_to_node_edge_counter
        )
        cluster_to_cluster_avg = self.__calculate_avg(
            ret_cluster_to_cluster_edge, ret_cluster_to_cluster_edge_counter
        )

        self.logger.debug("node_to_cluster_avg--" + str(node_to_cluster_avg))
        self.logger.debug("cluster_to_node_avg--" + str(cluster_to_node_avg))
        self.logger.debug("cluster_to_cluster_avg--" + str(cluster_to_cluster_avg))

        return (
            node_to_cluster_avg,
            cluster_to_node_avg,
            cluster_to_cluster_avg,
            ret_node_to_node_edge,
        )

    def __calculate_avg(
        self, ret_node_to_cluster_edge, ret_node_to_cluster_edge_counter
    ):
        result = {}
        for pair in ret_node_to_cluster_edge:
            result[pair] = round(
                ret_node_to_cluster_edge[pair] / ret_node_to_cluster_edge_counter[pair],
                2,
            )

        return result

    def __get_cluster_where_node(self, character, clustered_nodes):
        for cluster in clustered_nodes:
            if character in cluster:
                return cluster
        return None

    def __get_clustered_node(self, list_of_clustered_nodes, event):
        for cluster in list_of_clustered_nodes:
            cluster_events = cluster.split(self.cluster_seperator)
            if event in cluster_events:
                return cluster
        return None

    def __get_significance_dict_after_clustering(self, sign_after_sec_rule):
        ret_dict = {}
        for i in range(len(sign_after_sec_rule)):
            ret_dict[self.events[i]] = sign_after_sec_rule[i][0]
        return ret_dict

    def __add_normal_nodes_to_graph(
        self,
        graph,
        nodes_after_first_rule,
        list_of_clustered_nodes,
    ):
        for node in nodes_after_first_rule:
            if node not in list_of_clustered_nodes:
                w, h = self.calulate_node_size(node)
                node_sign = self.sign_dict.get(node)
                self.graph.add_event(node, node_sign, (w, h))

    def __convert_clustered_nodes_to_list(self, clustered_nodes):
        ret_nodes = []
        for event in clustered_nodes:
            cluster_events = event.split(self.cluster_seperator)
            for node in cluster_events:
                if node not in ret_nodes:
                    ret_nodes.append(node)
        return ret_nodes

    def __update_significance_matrix(
        self, sign_after_first_rule, clustered_nodes_after_sec_rule
    ):
        # go through each cluster
        # 1. find average sum of significance e.g. sig_a+sig_b/2
        # 2. don't change correlation, but consider current cluster as one node(a-b)
        for event in clustered_nodes_after_sec_rule:
            cluster_events = event.split(self.cluster_seperator)
            sign_after_first_rule = self.__calculate_sign_for_events(
                sign_after_first_rule, cluster_events
            )
        return sign_after_first_rule

    def __calculate_sign_for_events(self, significance_matrix, cluster_events):
        events_size = len(cluster_events)
        if events_size == 0:
            return significance_matrix
        sum = 0.0
        for i in range(len(self.events)):
            if self.events[i] in cluster_events:
                sum += significance_matrix[i][0]
        # put new sign for each row
        new_value = format(sum / events_size, ".2f")
        for i in range(len(self.events)):
            if self.events[i] in cluster_events:
                for j in range(len(self.events)):
                    significance_matrix[i][j] = new_value

        # print("putting new value: " + str(new_value))
        return significance_matrix

    def __calculate_clustered_nodes(
        self,
        nodes_after_first_rule,
        corr_after_first_rule,
        sign_after_first_rule,
        significance,
    ):
        main_cluster_list = []
        less_sign_nodes = []
        global_clustered_nodes = set()
        for a in range(len(self.events)):
            # 1. Find less significant nodes
            if (
                sign_after_first_rule[a][0] < significance
                and sign_after_first_rule[a][0] != -1
            ):
                less_sign_nodes.append(self.events[a])
        # 2. Find clusters of less significant nodes:
        for i in range(len(self.events)):
            if (
                self.events[i] not in less_sign_nodes
                or self.events[i] in global_clustered_nodes
            ):
                continue
            events_to_cluster = set()
            something_to_cluster = False
            for j in range(len(self.events)):
                # node will be checked horizontally and vertically (incoming and outgoing edges)
                # outgoing edges
                # first_possib = self.events[i] + self.events[j]
                # incoming edges
                # sec_possib = self.events[j] + self.events[i]
                if (
                    corr_after_first_rule[i][j] >= self.minimum_correlation
                    or corr_after_first_rule[j][i] >= self.minimum_correlation
                ):
                    events_to_cluster.add(self.events[i])
                    global_clustered_nodes.add(self.events[i])
                    if self.events[j] not in global_clustered_nodes:
                        events_to_cluster.add(self.events[j])
                        global_clustered_nodes.add((self.events[j]))
                        something_to_cluster = True

            if something_to_cluster:
                # special case if already all correlated nodes with current node clustered with other nodes, cluster
                # current node just by itself, it means all nodes already in global_clustered_nodes but not current node !

                # join events from set
                cluster = self.cluster_seperator.join(sorted(events_to_cluster))
                # check if permutation in cluster(true/false)
                if not self.__permutation_exists(cluster, main_cluster_list):
                    main_cluster_list.append(cluster)
            # add current node as cluster, special case - all correlated nodes already clustered!
            else:
                main_cluster_list.append(self.events[i])
        return main_cluster_list

    def __permutation_exists(self, current_cluster, main_cluster_list):
        sorted_cluster = sorted(current_cluster.split(self.cluster_seperator))

        for cluster in main_cluster_list:
            cluster_events = cluster.split(self.cluster_seperator)
            if sorted_cluster == sorted(cluster_events):
                return True
        return False

    def __add_clustered_nodes_to_graph(self, graph, nodes, sign_dict):
        counter = 1
        for cluster in nodes:
            cluster_events = cluster.split(self.cluster_seperator)
            string_cluster = "Cluster " + str(counter)
            # needed to later find the cluster id and to draw the edges
            self.cluster_id_mapping[cluster] = string_cluster
            sign = sign_dict.get(cluster_events[0])
            # print(string_cluster + ": " + str(cluster))
            self.graph.add_cluster(string_cluster, sign, (1.5, 1.0), cluster_events)
            counter += 1

    def __calculate_significant_nodes(self, corr_after_first_rule):
        # this function will be called after checking sign >= sign_slider therefore all nodes which are
        # not >= sign_slider will be replaced with -1. Therefor in this function will be checked if corr == -1
        ret_sign_nodes = []
        for i in range(len(self.events)):
            for j in range(len(self.events)):
                # print("checking if " + str(corr_after_first_rule[i][j]) + " is == -1 for " + str(self.events[i]))
                if (
                    corr_after_first_rule[i][j] != -1
                    and self.events[i] not in ret_sign_nodes
                ):
                    ret_sign_nodes.append(self.events[i])
        # print("sign-rr-> " + str(ret_sign_nodes))
        return ret_sign_nodes

    # __cluster_based_on_significance_dependency
    def __calculate_first_rule(
        self, events, correlation_of_nodes, significance_of_nodes, significance
    ):
        value_to_replace = -1
        indices_to_replace = set()
        # all possibilities minus itself
        node_correlation_poss = len(events) - 1
        for i in range(len(events)):
            counter = 0
            for j in range(len(events)):
                # remove self loops
                if i == j:
                    correlation_of_nodes[i][j] = 0.0
                    continue
                # these nodes are less significant and lowly correlated therefore have to be removed if
                # self.node_significance[i][j] < significance and self.correlation_of_nodes[i][j] < correlation and not self correlation
                # Ignore self correlation nodes for now
                if (
                    correlation_of_nodes[i][j] < self.minimum_correlation
                    and correlation_of_nodes[j][i] < self.minimum_correlation
                    and significance_of_nodes[i][j] < significance
                ):
                    counter += 1
                # if correlation_of_nodes[i][j] < self.minimum_correlation:
                #    correlation_of_nodes[i][j] = 0
            if node_correlation_poss == counter:
                indices_to_replace.add(i)

        indices_to_replace = list(indices_to_replace)

        correlation_of_nodes = np.array(correlation_of_nodes)
        significance_of_nodes = np.array(significance_of_nodes)

        correlation_of_nodes[indices_to_replace, :] = value_to_replace
        correlation_of_nodes[:, indices_to_replace] = value_to_replace

        significance_of_nodes[indices_to_replace, :] = value_to_replace
        # significance_of_nodes[:, indices_to_replace] = value_to_replace

        return correlation_of_nodes, significance_of_nodes

    """ to calculate the signification, we have to divide each nodes appearance by the most frequently node number
        asked ChatGpt how to do this"""

    def __calculate_significance(self):
        # find the most frequently node from of all events
        max_value = max(self.appearance_frequency.values())
        dict = {}
        # dict = {key: value / max_value for key, value in self.appearance_activities.items()}
        for key, value in self.appearance_frequency.items():
            new_sign = format(value / max_value, ".2f")
            dict[key] = new_sign
        return dict

    def __create_correlation_dependency_matrix(self):
        # create a matrix with the same shape and fill it with zeros
        correlation_matrix = np.zeros(self.succession_matrix.shape)
        outgoing_edges = np.sum(self.succession_matrix, axis=1)

        correlation_matrix = np.round(
            self.succession_matrix / outgoing_edges[:, np.newaxis], decimals=2
        )

        correlation_matrix = np.where(
            np.isnan(correlation_matrix), 0.0, correlation_matrix
        )

        return correlation_matrix

    def __calculate_node_significance_matrix(self, significance_values):
        ret_matrix = np.zeros(self.succession_matrix.shape)
        significance_column = np.array(
            list(significance_values.values()), dtype=np.float64
        )[:, np.newaxis]

        ret_matrix = ret_matrix + significance_column
        return ret_matrix

    def get_significance(self):
        return self.significance

    def get_correlation(self):
        return self.correlation

    def get_edge_cutoff(self):
        return self.edge_cutoff

    def get_utility_ratio(self):
        return self.utility_ratio
