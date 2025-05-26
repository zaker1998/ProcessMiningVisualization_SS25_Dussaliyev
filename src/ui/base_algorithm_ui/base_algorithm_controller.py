import streamlit as st
from abc import abstractmethod
from ui.base_ui.base_controller import BaseController
from transformations.dataframe_transformations import DataframeTransformations
from components.buttons import to_home
from exceptions.graph_exceptions import InvalidNodeNameException, GraphException
from exceptions.type_exceptions import TypeIsNoneException
from logger import get_logger


class BaseAlgorithmController(BaseController):
    """Base class for the algorithm controllers. It provides the basic methods for the algorithm controllers."""

    def __init__(
        self, views=None, mining_model_class=None, dataframe_transformations=None
    ):
        """Initializes the controller for the algorithm views.

        Parameters
        ----------
        views : List[BaseView] | BaseView, optional
            The views for the algorithm page. If None is passed, the default view is used, by default None
        mining_model_class : MiningInterface class, optional
            The class of the mining model, by default None
        dataframe_transformations : DataframeTransformations, optional
            The class for the dataframe transformations. If None is passed, a new instance is created, by default None
        """
        self.logger = get_logger("BaseAlgorithmController")

        self.mining_model = None

        if dataframe_transformations is None:
            dataframe_transformations = DataframeTransformations()

        self.dataframe_transformations = dataframe_transformations

        if mining_model_class is None:
            self.logger.error("Mining model class is None")
            raise TypeIsNoneException("Mining model class is None")

        self.mining_model_class = mining_model_class
        super().__init__(views)

    @abstractmethod
    def perform_mining(self) -> None:
        """Performs the mining of the algorithm. This method must be implemented by the subclass.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError("perform_mining() method not implemented")

    @abstractmethod
    def process_algorithm_parameters(self):
        """Processes the algorithm parameters from the streamlit session state. Either reads the parameters from the session state or sets default values that are used for the mining.
        This method must be implemented by the subclass.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError(
            "process_algorithm_parameters() method not implemented"
        )

    @abstractmethod
    def have_parameters_changed(self) -> bool:
        """Checks if the algorithm parameters have changed. This method must be implemented by the subclass.

        Returns
        -------
        bool
            True if the algorithm parameters have changed, False otherwise.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError("have_parameters_changed() method not implemented")

    @abstractmethod
    def get_sidebar_values(self) -> dict[str, any]:
        """Returns the values for the sidebar elements. Can be used to set minimum and maximum values for the sidebar sliders, that could depend on the model.
        This method must be implemented by the subclass.

        Returns
        -------
        dict[str, any]
            A dictionary containing the values for the sidebar elements. The keys of the dictionary are equal to the keys of the sliders.

        Raises
        ------
        NotImplementedError
            If the method is not implemented by the subclass.
        """
        raise NotImplementedError("get_sidebar_values() method not implemented")

    def is_correct_model_type(self, model) -> bool:
        """Checks if the model is of the correct type.

        Parameters
        ----------
        model : any
            The model to be checked.

        Returns
        -------
        bool
            True if the model is of the correct type, False otherwise.
        """
        return isinstance(model, self.mining_model_class)

    def create_empty_model(self, *log_data):
        """Creates an empty model instance. The method is used to create a model instance with the provided log data.
        The order of the log data must be the same as the order of the parameters of the create_mining_instance method of the mining model class.

        Returns
        -------
        MiningInterface
            An instance of the mining model class.
        """
        return self.mining_model_class.create_mining_instance(*log_data)

    def transform_df_to_log(self, df, **selected_columns) -> tuple:
        """Transforms the DataFrame to a log. The method uses the dataframe_transformations class to transform the DataFrame to a log.
        The selected columns are passed as keyword arguments to the 'DataframeTransformation' class. The method returns the log data that is used to create the mining model.
        Can be overridden by the subclass if additional transformations are needed.

        Parameters
        ----------
        df : pd.DataFrame
            The DataFrame to be transformed.

        Returns
        -------
        tuple
            The log data that is used to create the mining model.
        """
        self.dataframe_transformations.set_dataframe(df)
        return (
            self.dataframe_transformations.dataframe_to_cases_dict(
                timeLabel=selected_columns["time_column"],
                caseLabel=selected_columns["case_column"],
                eventLabel=selected_columns["activity_column"],
            ),
        )

    def process_session_state(self):
        """Processes the session state. If a model is already in the session state, it is checked if it is of the correct type. If not, an error message is displayed and the user is redirected to the home page.
        If no model is in the session state, a model is created from the provided DataFrame and selected columns. The model is stored in the session state.
        """
        super().process_session_state()
        if "model" in st.session_state:
            if not self.is_correct_model_type(st.session_state.model):
                self.logger.error(
                    f"Invalid model type. Expected model type: {str(self.mining_model_class)}, Received model type: {type(st.session_state.model)}"
                )
                self.logger.info("redirect to home page")
                st.session_state.error = f""" Invalid model type. 
                
                Expected model type: {str(self.mining_model_class)}, Received model type: {str(type(st.session_state.model))}
                """
                to_home("Home")
                st.rerun()
            self.mining_model = st.session_state.model
        else:
            if (
                "df" not in st.session_state
                or "selected_columns" not in st.session_state
            ):
                self.logger.error("DataFrame or selected columns are missing.")
                self.logger.info("redirect to home page")
                st.session_state.error = "A DataFrame and selected columns must be provided to create a model."
                to_home()
                st.rerun()
            log_data = self.transform_df_to_log(
                st.session_state.df, **st.session_state.selected_columns
            )
            st.session_state.model = self.create_empty_model(*log_data)
            self.mining_model = st.session_state.model

            del st.session_state.df
            del st.session_state.selected_columns

    def run(self, view, pos):
        """Runs the algorithm controller.

        Parameters
        ----------
        view : BaseAlgorithmView
            The view for the algorithm.
        pos : int
            The position of the algorithm in the sidebar.
        """
        self.process_algorithm_parameters()
        view.display_sidebar(self.get_sidebar_values())
        view.display_back_button()
        view.display_export_button(disabled=True)
        if self.have_parameters_changed() or self.mining_model.get_graph() is None:
            try:
                view.display_loading_spinner("Mining...", self.perform_mining)
            except InvalidNodeNameException as ex:
                self.logger.exception(ex)
                self.logger.error(
                    "Invalid node name. The string '___' is not allowed in node names."
                )
                st.session_state.error = (
                    ex.message
                    + "\n Please check the input data. The string '___' is not allowed in node names."
                )
                to_home()
                st.rerun()
            except GraphException as ex:
                self.logger.exception(ex)
                self.logger.warning(
                    "Graph could not be created. Wait until the mining is finished before changing parameters."
                )
                st.warning(
                    "Do not change the parameters while mining. This will cause an error. Wait until the mining is finished."
                )
        view.display_graph(self.mining_model.get_graph())
        view.display_export_button(disabled=False)
