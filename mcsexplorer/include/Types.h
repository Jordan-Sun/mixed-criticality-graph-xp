#ifndef TYPES_H
#define TYPES_H

#include <stdexcept>
#include <variant>

typedef enum {
    LO = 1,
    HI = 2,
} Criticality;

static inline Criticality int2crit(int value) {
    if (1 == value) return LO;
    if (2 == value) return HI;

    throw std::runtime_error("Unknown given value for criticality");
}

enum class SearchAlgorithm {
    // Dummy placeholder
    NONE,
    // Exact algorithms
    BFS,
    ACBFS,
    DFS,
    // Periodic counterparts
    PBFS,
    PACBFS,
    PDFS,
};

static inline std::string get_name(SearchAlgorithm algorithm) {
    switch (algorithm) {
        case SearchAlgorithm::BFS:
            return "BFS";
        case SearchAlgorithm::ACBFS:
            return "ACBFS";
        case SearchAlgorithm::DFS:
            return "DFS";
        case SearchAlgorithm::PBFS:
            return "PBFS";
        case SearchAlgorithm::PACBFS:
            return "PACBFS";
        case SearchAlgorithm::PDFS:
            return "PDFS";
        default:
            return "None";
    }
}

static inline std::string get_full_name(SearchAlgorithm algorithm) {
    switch (algorithm) {
        case SearchAlgorithm::BFS:
            return "Breadth First Search";
        case SearchAlgorithm::ACBFS:
            return "Antichain Breadth First Search";
        case SearchAlgorithm::DFS:
            return "Depth First Search";
        case SearchAlgorithm::PBFS:
            return "Periodic Breadth First Search";
        case SearchAlgorithm::PACBFS:
            return "Periodic Antichain Breadth First Search";
        case SearchAlgorithm::PDFS:
            return "Periodic Depth First Search";
        default:
            return "None";
    }
}

static inline SearchAlgorithm from_name(std::string name) {
    if ("bfs" == name) return SearchAlgorithm::BFS;
    if ("acbfs" == name) return SearchAlgorithm::ACBFS;
    if ("dfs" == name) return SearchAlgorithm::DFS;
    if ("pbfs" == name) return SearchAlgorithm::PBFS;
    if ("pacbfs" == name) return SearchAlgorithm::PACBFS;
    if ("pdfs" == name) return SearchAlgorithm::PDFS;
    if ("none" == name) return SearchAlgorithm::NONE;

    throw std::runtime_error("Unknown search algorithm name: " + name);
}

static inline bool uses_idle_antichain(SearchAlgorithm algorithm) {
    switch (algorithm) {
        case SearchAlgorithm::ACBFS:
        case SearchAlgorithm::PACBFS:
            return true;
        default:
            return false;
    }
}

typedef struct Result_t {
    SearchAlgorithm algorithm;
    bool is_safe = true;
    int depth = 0;
    u_int64_t visited_count = 0;
    u_int64_t duration_ns = 0;
} Result;

#endif /* TYPES_H */
