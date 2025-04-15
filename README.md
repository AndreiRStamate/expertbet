# ExpertBet

ExpertBet is a platform designed to provide users with expert insights and analytics for betting. This README outlines the project structure, setup instructions, and usage guidelines.

## Features

- Expert betting insights and analytics.
- User-friendly interface for predictions.
- Real-time data updates.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/expertbet.git
    ```
2. Navigate to the project directory:
    ```bash
    cd expertbet
    ```
3. Create a virtual environment:
    ```bash
    python3 -m venv venv
    ```
4. Activate the virtual environment:
    - On Linux/Mac:
        ```bash
        source venv/bin/activate
        ```
    - On Windows:
        ```bash
        venv\Scripts\activate
        ```
5. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

6. Run the program:
    ```bash
    python3 main.py <no_days>
    ```

Replace `<no_days>` with the number of days for which you want to fetch and analyze data.

Example:
```bash
python3 main.py 7
```

## Configuration

The `config.json` file is used to customize the behavior of the application. It includes the following settings:

- **leagues**: A list of league identifiers for which data will be fetched and analyzed. You can add or remove leagues as needed.
- **default_days**: The default number of days for which data will be fetched if no `<no_days>` argument is provided when running the program.
- **number_of_matches**: The maximum number of matches to display, sorted by predictability. If set to a negative value, all matches will be displayed.

### Example

To modify the leagues, default days, or number of matches, edit the `config.json` file:

```json
{
    "leagues": [
        "soccer_epl",
        "soccer_spain_la_liga",
        "soccer_italy_serie_a",
        "soccer_germany_bundesliga"
    ],
    "default_days": 1,
    "number_of_matches": 5
}
```

The application will automatically use these settings when executed.

## Template for Tip Files

The application uses a template file (`gpt-generated-5x3.txt`) to generate detailed betting tips for matches with high predictability (action: "Pariu sigur"). This template contains placeholders that are dynamically replaced with match-specific details, such as team names, league name, and match date and time.

### Template File Location

The template file is located in the `prompt-examples` folder

## Output File for Match Details

The application allows you to print match details to the terminal and optionally write them to an output file. This is controlled by the `output_file` parameter in the `print_match` function.

### How It Works

- If an `output_file` is specified, the match details will be appended to the specified file.
- If no `output_file` is provided, the match details will only be printed to the terminal.

### Example Usage

#### Printing Only to the Terminal
If you do not specify an output file, the match details will be displayed in the terminal:
```python
print_match(match, action)
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch:
    ```bash
    git checkout -b feature-name
    ```
3. Commit your changes:
    ```bash
    git commit -m "Add feature-name"
    ```
4. Push to your branch:
    ```bash
    git push origin feature-name
    ```
5. Open a pull request.

## License

This project is licensed under the [MIT-0 License](LICENSE).

## Contact

For questions or feedback, please contact [roomer.palest.7h@icloud.com].
