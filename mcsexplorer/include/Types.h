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

enum class ExactAlgorithm { BFS, ACBFS };

static inline bool _uses_idle_antichain(ExactAlgorithm exact_algorithm) {
    return exact_algorithm == ExactAlgorithm::ACBFS;
}

static inline std::string _get_name(ExactAlgorithm exact_algorithm) {
    switch (exact_algorithm) {
        case ExactAlgorithm::BFS:
            return "BFS";
        case ExactAlgorithm::ACBFS:
            return "ACBFS";
    }
    return "UnknownExactAlgorithm";
}

enum class PilotHeuristics { BFS, ACBFS };

static inline bool _uses_idle_antichain(PilotHeuristics pilot_heuristic) {
    return pilot_heuristic == PilotHeuristics::ACBFS;
}

static inline std::string _get_name(PilotHeuristics pilot_heuristic) {
    switch (pilot_heuristic) {
        case PilotHeuristics::BFS:
            return "PBFS";
        case PilotHeuristics::ACBFS:
            return "PACBFS";
    }
    return "UnknownPilotHeuristic";
}

typedef std::variant<ExactAlgorithm, PilotHeuristics> SearchAlgorithm;

static inline bool uses_idle_antichain(SearchAlgorithm algorithm) {
    return std::visit([](auto&& alg) { return _uses_idle_antichain(alg); }, algorithm);
}

static inline std::string get_name(SearchAlgorithm algorithm) {
    return std::visit([](auto&& alg) { return _get_name(alg); }, algorithm);
}

typedef struct Result_t {
    std::variant<ExactAlgorithm, PilotHeuristics> algorithm;
    bool is_safe = true;
    int depth = 0;
    u_int64_t visited_count = 0;
    u_int64_t duration_ns = 0;
} Result;

#endif /* TYPES_H */
