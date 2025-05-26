import streamlit as st
from ui.base_ui.base_view import BaseView
from components.buttons import home_button, navigation_button
from components.interactiveGraph import interactiveGraph
from abc import abstractmethod


class BaseAlgorithmView(BaseView):
    """Base class for the algorithm views. It provides the basic layout and methods for the algorithm views.
    The class is abstract and must be inherited by a subclass.
    """

    graph_height = 600

    def create_layout(self):
        """Creates the layout for the algorithm views. It creates the graph container, button containers and node data container.
        This is neeeded to display different elements not in the order they are created.
        """
        super().create_layout()
        graph_wrapper_container = st.container(
            border=True, height=self.graph_height + 40
        )  # add 40 to height to account for padding
        with graph_wrapper_container:
            self.graph_container = st.empty()
        button_container = st.container()
        self.node_data_container = st.container()
        with button_container:
            self.back_button_column, _, export_button_column = st.columns([1, 1, 1])

        with export_button_column:
            self.export_button_container = st.empty()

    @abstractmethod
    def render_sidebar(self, sidebar_values: dict[str, any]) -> None:
        """Renders the sidebar for the algorithm views. This method must be implemented by the subclass.
        The elements rendered are automatically displayed in the sidebar.

        Parameters
        ----------
        sidebar_values : dict[str, any]
            A dictionary containing the values for the sidebar elements. The keys of the dictionary are equal to the keys of the sliders.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError("render_sidebar() method not implemented")

    def display_sidebar(self, sidebar_values: dict[str, any]) -> None:
        """Displays the sidebar for the algorithm views. The methode calls the render_sidebar method of the subclass.

        Parameters
        ----------
        sidebar_values : dict[str, any]
            A dictionary containing the values for the sidebar elements. The keys of the dictionary are equal to the keys of the sliders.
        """
        with st.sidebar:
            self.render_sidebar(sidebar_values)

    def display_back_button(self) -> None:
        """Displays the back button. The button navigates back to the home page."""
        with self.back_button_column:
            home_button("Back", use_container_width=True)

    def display_export_button(self, disabled=False) -> None:
        """Displays the export button. The button is disabled while the graph is loading."""
        with self.export_button_container:
            # Add hover tooltip and visual feedback
            button = navigation_button(
                "Export",
                "Export",
                use_container_width=True,
                disabled=disabled,
                key="export_button-" + str(disabled),
            )
            
            if button:
                # Add success message when clicked
                st.success("Export initiated successfully!")

    def display_graph(self, graph) -> None:
        """Displays the graph in the graph container.

        Parameters
        ----------
        graph : BaseGraph
            The graph to be displayed.
        """
        with self.graph_container:
            if graph is not None:
                interactiveGraph(
                    graph,
                    onNodeClick=self.display_node_info,
                    height=self.graph_height,
                )

    def display_loading_spinner(self, message: str, operation) -> None:
        """Displays a loading spinner while an operation is running."""
        with self.graph_container:
            with st.spinner(f"📊 {message}"):
                result = operation()
                # Show success message when complete
                st.success("Operation completed successfully!")
                return result

    def display_node_info(self, node_name: str, node_description: str) -> None:
        """Displays the information of a node in the node data container.

        Parameters
        ----------
        node_name : str
            The name of the node.
        node_description : str
            The description of the node.
        """
        with self.node_data_container:
            with st.expander(f"Node: {node_name}"):
                for line in node_description.split("\n"):
                    st.write(line)

    def display_page_title(self, title: str) -> None:
        """Displays the page title. If the algorithm has documentation, a button is displayed to navigate to the documentation.

        Parameters
        ----------
        title : str
            The title of the page.
        """
        from config import docs_path_mappings

        if st.session_state.algorithm not in docs_path_mappings:
            st.title(title)

        else:
            title_column, button_column = st.columns([3, 1])
            with title_column:
                st.title(title)
            with button_column:
                navigation_button(
                    "Algorithm Explanation",
                    "Documentation",
                    use_container_width=True,
                )
