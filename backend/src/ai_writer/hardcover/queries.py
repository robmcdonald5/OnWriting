"""GraphQL query constants for the Hardcover API.

All queries stay within depth limit of 3: books -> contributions -> author.
"""

# Fields shared across all book queries
_BOOK_FIELDS = """
    id
    title
    slug
    rating
    ratings_count
    users_read_count
    cached_tags
    description
    release_date
    pages
    contributions {
        author {
            name
            slug
        }
    }
    editions(
        where: {isbn_13: {_is_null: false}}
        limit: 1
    ) {
        isbn_13
        isbn_10
    }
"""

TOP_RATED_BOOKS = (
    """
query TopRatedBooks($min_ratings: Int!, $limit: Int!, $offset: Int!) {
    books(
        where: {ratings_count: {_gte: $min_ratings}}
        order_by: {rating: desc}
        limit: $limit
        offset: $offset
    ) {
        %s
    }
}
"""
    % _BOOK_FIELDS
)

MOST_READ_BOOKS = (
    """
query MostReadBooks($min_read: Int!, $limit: Int!, $offset: Int!) {
    books(
        where: {users_read_count: {_gte: $min_read}}
        order_by: {users_read_count: desc}
        limit: $limit
        offset: $offset
    ) {
        %s
    }
}
"""
    % _BOOK_FIELDS
)

SEARCH_BOOKS = """
query SearchBooks($query: String!, $per_page: Int!) {
    search(query: $query, query_type: "books", per_page: $per_page) {
        ids
    }
}
"""

BOOK_BY_IDS = (
    """
query BooksByIds($ids: [Int!]!) {
    books(where: {id: {_in: $ids}}) {
        %s
    }
}
"""
    % _BOOK_FIELDS
)

LIST_BOOKS = (
    """
query ListBooks($id: Int!) {
    lists_by_pk(id: $id) {
        list_books {
            book {
                %s
            }
        }
    }
}
"""
    % _BOOK_FIELDS
)
