import asyncio
import math
from collections.abc import Coroutine
from typing import Any, TypeVar

import matplotlib.pyplot as plt
import nltk
import pandas as pd
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from selectolax.parser import HTMLParser
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import trange

from database.methods import add_exam_number_to_problems, get_problems_with_details
from specifiers import BaseSpecifier, informatics_specifier_2024

T = TypeVar("T")


def _run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)


async def get_theme_df(
    content_codifier_theme_id: str, specifier: BaseSpecifier = informatics_specifier_2024
) -> pd.DataFrame:
    return await get_problems_with_details(
        gia_type=specifier.gia_type,
        subject_name=specifier.subject_name,
        content_codifier_theme_id=content_codifier_theme_id,
    )


def get_problem_text(html: str, strip: bool = True, parser: str = "beautifulsoup") -> str:
    if parser == "beautifulsoup":
        soup = BeautifulSoup(html, features="html.parser")
        return str(soup.get_text(strip=strip))
    if parser == "selectolax":
        parser = HTMLParser(html=html)
        return str(parser.text(strip=strip))
    raise (ValueError(f'parser should be "beautifulsoup" or "selectolax", not {parser}'))


async def print_theme_problem_condition(
    content_codifier_theme_id: str,
    index: int = 0,
    print_all_problems: bool = False,
) -> None:
    theme_df = await get_theme_df(content_codifier_theme_id)
    if theme_df.empty:
        print(f"No problems found with {content_codifier_theme_id=}")
        return
    print(f"Theme {content_codifier_theme_id}; {len(theme_df)} problems:\n")
    if not print_all_problems:
        problem_series = theme_df.iloc[index]
        problem_html = problem_series["condition_html"]
        condition_text = get_problem_text(problem_html)
        print(condition_text)
    else:
        for index, row in theme_df.iterrows():
            condition_text = get_problem_text(row["condition_html"])
            print(f"{row['url']}: {condition_text}")


async def print_all_exam_number_problems(
    exam_number: int, specifier: BaseSpecifier = informatics_specifier_2024
) -> None:
    first_number = 1
    last_number = specifier.problems[-1].exam_number
    if not ((isinstance(exam_number, int)) or (first_number <= abs(exam_number) <= last_number)):
        raise (
            ValueError(
                f"exam_number should be integer between {first_number} "
                f"and {last_number}, not {exam_number}"
            )
        )
    for theme_codifier_id in specifier.problems[exam_number - 1].content_codifier_theme_ids:
        await print_theme_problem_condition(theme_codifier_id, print_all_problems=True)


async def set_exam_number(
    exam_number: int, problem_ids: list[str] | None = None, content_codifier_theme_id: str = ""
) -> None:
    if content_codifier_theme_id:
        theme_df = await get_theme_df(content_codifier_theme_id=content_codifier_theme_id)
        problem_ids = theme_df["problem_id"].tolist()
    if problem_ids:
        await add_exam_number_to_problems(problem_ids=problem_ids, exam_number=exam_number)
        print(f'Set "{exam_number}" exam number to {len(problem_ids)} problems.')
        return
    raise ValueError("Set problem_ids or content_codifier_theme_id argument")


def print_clustered_df(clustered_df: pd.DataFrame) -> None:
    grouped_df = clustered_df.groupby("cluster_label")
    for cluster_label, cluster_data in grouped_df:
        print(f"Cluster {cluster_label}:\n")
        for index, row in cluster_data.iterrows():
            condition_text = get_problem_text(row["condition_text"])
            print(f"{row['url']}: {condition_text}")
        print("\n\n", end="")


def clusterize_tasks_elbow_method(
    df: pd.DataFrame,
    max_n_clusters: int = 10,
    optimal_n_clusters: int | None = None,
    x_ticks_rotation: int | None = None,
    y_ticks_rotation: int | None = None,
    horizontal_lines: bool = False,
    x_step: int = 1,
    y_step: int = 10,
) -> pd.DataFrame:
    nltk.download("stopwords")
    russian_stop_words = stopwords.words("russian")

    # Create a TfidfVectorizer object to transform text data into numerical features
    tfidf_vectorizer = TfidfVectorizer(min_df=2, stop_words=russian_stop_words)

    # Transform text into numerical features
    data = tfidf_vectorizer.fit_transform(df["condition_text"])

    # Plot inertia graph for different numbers of clusters
    max_n_clusters_ = min(max_n_clusters + 1, len(df))
    inertia_list = []
    for k in trange(1, max_n_clusters_, desc="Clustering progress"):
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(data)
        inertia_list.append(kmeans.inertia_)

    # Determine the optimal number of clusters (k) using the elbow method
    plt.figure(figsize=(12, 10))
    plt.plot(range(1, max_n_clusters_), inertia_list, marker="o")
    plt.xlabel("Number of clusters")
    plt.ylabel("Inertia")
    plt.xticks(
        range(1, x_step * (math.ceil(max_n_clusters_ / x_step) + 1), x_step),
        rotation=x_ticks_rotation,
    )
    plt.yticks(
        range(0, y_step * (math.ceil(max(inertia_list) / y_step) + 1), y_step),
        rotation=y_ticks_rotation,
    )
    plt.title("Elbow Method")
    if horizontal_lines:
        for idx, inertia in enumerate(inertia_list):
            plt.hlines(inertia, 0, idx + 1, colors="gray")

    plt.show()

    # Choose the optimal number of clusters
    if optimal_n_clusters is None:
        optimal_n_clusters = int(input("Enter the optimal number of clusters: "))

    kmeans_optimal = KMeans(n_clusters=optimal_n_clusters, random_state=42)
    kmeans_optimal.fit(data)
    df["cluster_label"] = kmeans_optimal.labels_

    return df


async def print_and_get_theme_clustered_df(
    content_codifier_theme_id: str | list[str],
    print_problem_clusters: bool = True,
    max_n_clusters: int = 10,
    optimal_n_clusters: int | None = None,
    x_ticks_rotation: int | None = None,
    y_ticks_rotation: int | None = None,
    horizontal_lines: bool = False,
    df: pd.DataFrame | None = None,
    x_step: int = 1,
    y_step: int = 10,
) -> pd.DataFrame:
    if df is None:
        if isinstance(content_codifier_theme_id, str):
            theme_df = await get_theme_df(content_codifier_theme_id=content_codifier_theme_id)
        elif isinstance(content_codifier_theme_id, list):
            theme_df = pd.concat(
                [
                    await get_theme_df(content_codifier_theme_id=theme_id)
                    for theme_id in content_codifier_theme_id
                ]
            )
        else:
            raise ValueError(
                f"content_codifier_theme_id should be str or list[str], not {type(content_codifier_theme_id)}"
            )

    else:
        theme_df = df.copy()
    if theme_df.empty:
        raise ValueError(f"No problems in database with {content_codifier_theme_id=}")
    theme_df["condition_text"] = theme_df["condition_html"].apply(
        lambda html: get_problem_text(html=html)
    )
    theme_df.drop("condition_html", axis=1, inplace=True)

    clustered_theme_df = clusterize_tasks_elbow_method(
        df=theme_df,
        max_n_clusters=max_n_clusters,
        optimal_n_clusters=optimal_n_clusters,
        x_ticks_rotation=x_ticks_rotation,
        y_ticks_rotation=y_ticks_rotation,
        horizontal_lines=horizontal_lines,
        x_step=x_step,
        y_step=y_step,
    )
    print(
        "Number of problems in clusters: "
        f"{clustered_theme_df['cluster_label'].value_counts(dropna=False).to_dict()}\n"
    )

    if print_problem_clusters:
        print_clustered_df(clustered_df=clustered_theme_df)
    return clustered_theme_df


async def set_exam_number_from_clustered_df(
    clustered_df: pd.DataFrame,
    cluster_id_to_exam_number: dict[int, int],
    specifier: BaseSpecifier = informatics_specifier_2024,
) -> None:
    """
    Sets the exam number based on the clustered task data.

    Args:
        - clustered_df: DataFrame containing clustered tasks.
          It should contain a column 'cluster_label' indicating the cluster number for each task.
        - cluster_id_to_exam_number: Dictionary mapping cluster numbers
          to exam numbers. Keys of the dictionary are cluster numbers, and values are exam numbers.
        - specifier: Subject specifier

    Returns:
        None
    """
    first_number = 1
    last_number = specifier.problems[-1].exam_number

    if not all(
        first_number <= abs(exam_number) <= last_number
        for exam_number in cluster_id_to_exam_number.values()
    ):
        raise ValueError(
            "All exam numbers in cluster_id_to_exam_number should be "
            f"within the range from {first_number} to {last_number}."
        )

    if set(clustered_df["cluster_label"].unique()) != set(cluster_id_to_exam_number.keys()):
        raise ValueError(
            "The set of keys in cluster_id_to_exam_number should "
            "match the set of unique cluster labels."
        )

    grouped_df = clustered_df.groupby("cluster_label")

    for cluster_label, cluster_data in grouped_df:
        exam_number = cluster_id_to_exam_number[cluster_label]

        problem_ids = cluster_data["problem_id"].tolist()

        await add_exam_number_to_problems(problem_ids=problem_ids, exam_number=exam_number)
        print(f'Set "{exam_number}" exam number to {len(problem_ids)} problems.')


def create_cluster_id_to_exam_number_dict(
    exam_number: int,
    actual_cluster_ids: list[int],
    outdated_cluster_ids: list[int],
    another_number_cluster_ids: list[int] | None = None,
) -> dict[int, int]:
    if another_number_cluster_ids is None:
        another_number_cluster_ids = []
    return (
        dict.fromkeys(actual_cluster_ids, exam_number)
        | dict.fromkeys(outdated_cluster_ids, exam_number * -1)
        | dict.fromkeys(another_number_cluster_ids)
    )


if __name__ == "__main__":
    asyncio.run(print_and_get_theme_clustered_df("3.2", max_n_clusters=20, x_ticks_rotation=45))
    # print(asyncio.run(get_theme_df("2.10")))
    # print(_run_async(get_theme_df("2.10")))
