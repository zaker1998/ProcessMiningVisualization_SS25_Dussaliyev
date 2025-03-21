from streamlit.runtime.uploaded_file_manager import UploadedFile
import pandas as pd
import pickle
import base64
import pm4py
from pm4py.objects.log.obj import EventLog
import tempfile
import os


class ImportOperations:

    def read_csv(
        self, filePath: str | UploadedFile, delimiter: str = ","
    ) -> pd.DataFrame:
        """Reads a csv file and returns a pandas DataFrame

        Parameters
        ----------
        filePath : str | UploadedFile
            Path to the csv file or the uploaded file object
        delimiter : str, optional
            The delimiter used in the csv file, by default ","

        Returns
        -------
        pd.DataFrame
            The csv file as a pandas DataFrame
        """
        df = pd.read_csv(filePath, delimiter=delimiter)
        return df

    def read_img(self, file_path: str) -> str:
        """Reads an image file and returns it as a base64 string. This is used to display the image in the HTML

        Parameters
        ----------
        file_path : str
            Path to the image file

        Returns
        -------
        str
            The image file as a base64 string
        """
        with open(file_path, "rb") as file:
            png = file.read()
        # https://pmbaumgartner.github.io/streamlitopedia/sizing-and-images.html
        # https://discuss.streamlit.io/t/how-to-show-local-gif-image/3408/2
        # Convert the image to a base64 string to be able to display it in the HTML
        png_base64 = base64.b64encode(png).decode("utf-8")
        return png_base64

    def read_model(self, path: str | UploadedFile) -> object:
        """Reads a model from a pickle file and returns the model object

        Parameters
        ----------
        path : str | UploadedFile
            Path to the pickle file or the uploaded file object

        Returns
        -------
        object
            The model object
        """
        if isinstance(path, UploadedFile):
            model = pickle.load(path)
        else:
            with open(path, "rb") as file:
                model = pickle.load(file)
        return model

    def read_file(self, file_path: str | UploadedFile) -> str:
        """Reads a file and returns the content as a string. This is used to display the content of the file in the UI

        Parameters
        ----------
        file_path : str | UploadedFile
            Path to the file or the uploaded file object

        Returns
        -------
        str
            The content of the file as a string
        """
        if isinstance(file_path, UploadedFile):
            return file_path.read().decode("utf-8")

        with open(file_path, "r") as file:
            return file.read()

    def read_file_binary(self, file_path: str) -> bytes:
        """Reads a file and returns the content as bytes. This is used to download the file

        Parameters
        ----------
        file_path : str
            Path to the file

        Returns
        -------
        bytes
            The content of the file as bytes
        """
        with open(file_path, "rb") as file:
            return file.read()

    def read_line(self, file_path: str | UploadedFile) -> str:
        """Reads the first line of a file and returns it as a string. This is used to detect the delimiter of a csv file

        Parameters
        ----------
        file_path : str | UploadedFile
            Path to the file or the uploaded file object

        Returns
        -------
        str
            The first line of the file as a string
        """
        if isinstance(file_path, UploadedFile):
            line = file_path.readline().decode("utf-8")
            # reset the file pointer to the beginning of the file
            file_path.seek(0)
            return line

        with open(file_path, "r") as file:
            return file.readline()

    def read_xes(self, file_path: str | UploadedFile) -> EventLog:
        """Reads an XES file and returns a PM4Py EventLog object

        Parameters
        ----------
        file_path : str | UploadedFile
            Path to the XES file or the uploaded file object

        Returns
        -------
        EventLog
            The XES file as a PM4Py EventLog object
        """
        if isinstance(file_path, UploadedFile):
            # Create a temporary file to store the uploaded content
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xes') as temp_file:
                temp_file.write(file_path.getvalue())
                temp_path = temp_file.name
            
            # Read the XES file using PM4Py
            event_log = pm4py.read_xes(temp_path)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            return event_log
        else:
            # Read directly from the file path
            return pm4py.read_xes(file_path)
    
    def xes_to_dataframe(self, event_log: EventLog) -> pd.DataFrame:
        """Converts a PM4Py EventLog object to a pandas DataFrame

        Parameters
        ----------
        event_log : EventLog
            The PM4Py EventLog object

        Returns
        -------
        pd.DataFrame
            The event log as a pandas DataFrame
        """
        return pm4py.convert_to_dataframe(event_log)

    def read_excel(self, filePath: str | UploadedFile, sheet_name: str = None) -> pd.DataFrame:
        """Reads an Excel file and returns a pandas DataFrame

        Parameters
        ----------
        filePath : str | UploadedFile
            Path to the Excel file or the uploaded file object
        sheet_name : str, optional
            Name of the sheet to read. If None, reads the first sheet.

        Returns
        -------
        pd.DataFrame
            The Excel file as a pandas DataFrame
        """
        df = pd.read_excel(filePath, sheet_name=sheet_name)
        return df

    def read_json(self, filePath: str | UploadedFile) -> pd.DataFrame:
        """Reads a JSON file and returns a pandas DataFrame

        Parameters
        ----------
        filePath : str | UploadedFile
            Path to the JSON file or the uploaded file object

        Returns
        -------
        pd.DataFrame
            The JSON file as a pandas DataFrame
        """
        df = pd.read_json(filePath)
        return df

    def read_xml(self, filePath: str | UploadedFile) -> pd.DataFrame:
        """Reads an XML file and returns a pandas DataFrame

        Parameters
        ----------
        filePath : str | UploadedFile
            Path to the XML file or the uploaded file object

        Returns
        -------
        pd.DataFrame
            The XML file as a pandas DataFrame
        """
        df = pd.read_xml(filePath)
        return df

    def read_parquet(self, filePath: str | UploadedFile) -> pd.DataFrame:
        """Reads a Parquet file and returns a pandas DataFrame

        Parameters
        ----------
        filePath : str | UploadedFile
            Path to the Parquet file or the uploaded file object

        Returns
        -------
        pd.DataFrame
            The Parquet file as a pandas DataFrame
        """
        df = pd.read_parquet(filePath)
        return df
