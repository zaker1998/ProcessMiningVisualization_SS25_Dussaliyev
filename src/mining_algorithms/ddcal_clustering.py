from clustering.ddcal import DDCAL


class DensityDistributionClusterAlgorithm:
    """A class to cluster the frequencies of the events in a log using the Density Distribution Cluster Algorithm (DDCAL)."""

    def __init__(self, frequencies):
        """Constructor for the DensityDistributionClusterAlgorithm class.

        Parameters
        ----------
        frequencies : list[int | float]
            A list of frequencies of the events
        """
        cluster_num = len(set(frequencies))
        max_cluster = 8
        if cluster_num > max_cluster:
            cluster_num = max_cluster
        ddcal = DDCAL(
            n_clusters=cluster_num,
            feature_boundary_min=0.1,
            feature_boundary_max=0.49,
            num_simulations=20,
            q_tolerance=0.45,
            q_tolerance_increase_step=0.5,
        )
        # execute DDCAL algorithm
        ddcal.fit(frequencies)

        # the usefull arrays:
        self.sorted_data = ddcal.sorted_data
        self.labels_sorted_data = ddcal.labels_sorted_data
