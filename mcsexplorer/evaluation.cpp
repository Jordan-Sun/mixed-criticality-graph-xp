#include "Graph.h"
#include "Job.h"
#include "SafeOracle.h"
#include "Scheduler.h"
#include "State.h"
#include "UnsafeOracle.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

static inline void print_results(const int test_case_id, const std::string scheduler, const std::string safe_oracles,
                                 const std::string unsafe_oracles, const std::vector<Result>& results,
                                 std::ostream& out1, std::ostream& out2) {
    std::stringstream search_result_csv_line;
    search_result_csv_line << test_case_id << "," << scheduler << "," << safe_oracles << "," << unsafe_oracles << ",";
    for (const auto& result : results) {
        search_result_csv_line << get_name(result.algorithm) << "," << result.is_safe << "," << result.depth << ","
                               << result.visited_count << "," << result.duration_ns << ",";
    }
    out1 << search_result_csv_line.str() << std::endl;
    out2 << search_result_csv_line.str() << std::endl;
}

void statespace_antichain_experiment(State* initial_state, int test_case_id, std::string output_path) {
    std::ofstream output_file;
    output_file.open(output_path, std::ios::in | std::ios::out | std::ios::ate);

    Graph g(initial_state, &Scheduler::edfvd, "", -1, {}, {});

    print_results(test_case_id, "EDF-VD", "None", "None", g.search({SearchAlgorithm::NONE, SearchAlgorithm::BFS}),
                  std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "None", g.search({SearchAlgorithm::NONE, SearchAlgorithm::ACBFS}),
                  std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "None", g.search({SearchAlgorithm::PACBFS, SearchAlgorithm::ACBFS}),
                  std::cout, output_file);

    output_file.close();
};

void statespace_antichain_oracle_experiment(State* initial_state, int test_case_id, std::string output_path) {
    std::ofstream output_file;
    output_file.open(output_path, std::ios::in | std::ios::out | std::ios::ate);

    Graph g(initial_state, &Scheduler::edfvd, "", -1, {}, {});
    std::vector<SearchAlgorithm> exact_bfs{SearchAlgorithm::NONE, SearchAlgorithm::BFS};
    std::vector<SearchAlgorithm> exact_acbfs{SearchAlgorithm::NONE, SearchAlgorithm::ACBFS};
    std::vector<SearchAlgorithm> pf_acbfs{SearchAlgorithm::PACBFS, SearchAlgorithm::ACBFS};

    print_results(test_case_id, "EDF-VD", "None", "None", g.search(exact_bfs), std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "None", g.search(exact_acbfs), std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "None", g.search(pf_acbfs), std::cout, output_file);

    g.set_unsafe_oracle(&UnsafeOracle::hi_over_demand);

    print_results(test_case_id, "EDF-VD", "None", "hi_interference", g.search(exact_bfs), std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "hi_interference", g.search(exact_acbfs), std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "None", "hi_interference", g.search(pf_acbfs), std::cout, output_file);

    output_file.close();
};

void statespace_oracle_experiment(State* initial_state, int test_case_id, std::string output_path) {
    std::ofstream output_file;
    output_file.open(output_path, std::ios::in | std::ios::out | std::ios::ate);

    Graph g(initial_state, &Scheduler::edfvd, "", -1, {}, {});
    std::vector<SearchAlgorithm> exact_acbfs{SearchAlgorithm::NONE, SearchAlgorithm::ACBFS};

    print_results(test_case_id, "EDF-VD", "None", "None", g.search(exact_acbfs), std::cout, output_file);

    g.set_safe_oracle(&SafeOracle::all_idle_hi);
    print_results(test_case_id, "EDF-VD", "None", "all_idle_hi", g.search(exact_acbfs), std::cout, output_file);

    g.clear_safe_oracle();
    g.set_safe_oracle(&SafeOracle::edf_carryoverjobs);
    print_results(test_case_id, "EDF-VD", "None", "edf_carryoverjobs", g.search(exact_acbfs), std::cout, output_file);

    g.clear_safe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::over_demand);
    print_results(test_case_id, "EDF-VD", "None", "interference", g.search(exact_acbfs), std::cout, output_file);

    g.clear_safe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::hi_over_demand);
    print_results(test_case_id, "EDF-VD", "None", "hi_interference", g.search(exact_acbfs), std::cout, output_file);

    g.clear_unsafe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::laxity);
    print_results(test_case_id, "EDF-VD", "None", "laxity", g.search(exact_acbfs), std::cout, output_file);

    g.clear_unsafe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::worst_laxity);
    print_results(test_case_id, "EDF-VD", "None", "worst_laxity", g.search(exact_acbfs), std::cout, output_file);

    g.clear_unsafe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::sum_sorted_laxities);
    print_results(test_case_id, "EDF-VD", "None", "sum_sorted_laxities", g.search(exact_acbfs), std::cout, output_file);

    g.clear_unsafe_oracle();
    g.set_unsafe_oracle(&UnsafeOracle::sum_sorted_worst_laxities);
    print_results(test_case_id, "EDF-VD", "None", "sum_sorted_worst_laxities", g.search(exact_acbfs), std::cout, output_file);

    output_file.close();
};

// void make_graph_experiment(State* initial_state, int test_case_id, std::string output_path) {
//     std::ofstream output_file;
//     output_file.open(output_path, std::ios::in | std::ios::out | std::ios::ate);

//     std::stringstream search_result_csv_line;
//     int64_t* search_result;

//     Graph g(initial_state, &Scheduler::edfvd, "", -1, {}, {});

//     search_result = g.acbfs();
//     search_result_csv_line.str("");
//     search_result_csv_line << test_case_id << ",None," << search_result[0] << "," << search_result[1] << ","
//                            << search_result[2] << "," << search_result[3] << std::endl;
//     std::cout << search_result_csv_line.str();
//     output_file << search_result_csv_line.str();

//     g.clear_unsafe_oracle();
//     g.set_unsafe_oracle(&UnsafeOracle::over_demand);
//     search_result = g.acbfs();
//     search_result_csv_line.str("");
//     search_result_csv_line << test_case_id << ",over_demand," << search_result[0] << "," << search_result[1] << ","
//                            << search_result[2] << "," << search_result[3] << std::endl;
//     std::cout << search_result_csv_line.str();
//     output_file << search_result_csv_line.str();

//     g.clear_unsafe_oracle();
//     g.set_unsafe_oracle(&UnsafeOracle::hi_over_demand);
//     search_result = g.acbfs();
//     search_result_csv_line.str("");
//     search_result_csv_line << test_case_id << ",hi_over_demand," << search_result[0] << "," << search_result[1] << ","
//                            << search_result[2] << "," << search_result[3] << std::endl;
//     std::cout << search_result_csv_line.str();
//     output_file << search_result_csv_line.str();

//     output_file.close();
// };

void scheduling_performance_experiment(State* initial_state, int test_case_id, std::string output_path) {
    std::ofstream output_file;
    output_file.open(output_path, std::ios::in | std::ios::out | std::ios::ate);

    Graph g(new State(*initial_state), &Scheduler::edfvd, "", -1, {&SafeOracle::all_idle_hi},
            {&UnsafeOracle::hi_over_demand});
    std::vector<SearchAlgorithm> exact_acbfs{SearchAlgorithm::NONE, SearchAlgorithm::ACBFS};
    std::vector<SearchAlgorithm> pf_acbfs{SearchAlgorithm::PACBFS, SearchAlgorithm::ACBFS};

    print_results(test_case_id, "EDF-VD", "all_idle_hi", "hi_interference", g.search(exact_acbfs),
                  std::cout, output_file);
    print_results(test_case_id, "EDF-VD", "all_idle_hi", "hi_interference", g.search(pf_acbfs), std::cout,
                  output_file);

    Graph g2(new State(*initial_state), &Scheduler::lwlf, "", -1, {&SafeOracle::all_idle_hi},
             {&UnsafeOracle::hi_over_demand});

    print_results(test_case_id, "LWLF", "all_idle_hi", "hi_interference", g2.search(exact_acbfs), std::cout,
                  output_file);
    print_results(test_case_id, "LWLF", "all_idle_hi", "hi_interference", g2.search(pf_acbfs), std::cout,
                  output_file);

    output_file.close();

    delete initial_state;
};

void read_task_sets(std::string const& input_path, std::string const& output_path,
                    std::function<void(State*, int, std::string)> experiment, int offset = 0, int n_experiments = -1) {
    std::ifstream input_file(input_path);
    if (!input_file.is_open()) {
        std::cerr << "Problem opening input file: " << input_path << std::endl;
        std::cerr << "Current directory: " << std::filesystem::current_path() << std::endl;

        exit(1);
    }

    int t;  // n test cases
    int n;  // n tasks in test case
    int T, D, X, c1, c2;
    std::vector<Job*> jobs;
    int end;

    input_file >> t;

    if (n_experiments == -1) {
        end = t;
    } else {
        end = offset + n_experiments;
    }

    for (int i = 0; i < end; i++) {
        input_file >> n;
        for (int j = 0; j < n; j++) {
            input_file >> T >> D >> X;
            input_file >> c1 >> c2;
            if (i >= offset) {
                Job* job = new Job(T, D, int2crit(X), std::vector<int>{c1, c2});
                jobs.push_back(job);
            }
        }
        if (i >= offset) {
            State* initial_state = new State(jobs);
            experiment(initial_state, i, output_path);
        }
        jobs.clear();
    }
};

void output_file_setup(std::string const& output_path, size_t max_algorithms = 1) {
    std::ofstream output_file;
    output_file.open(output_path);

    output_file << "tid,scheduler,safe,unsafe";
    for (size_t i = 0; i < max_algorithms; i++) {
        output_file << ",search_type_" << i 
                    << ",schedulable_" << i 
                    << ",depth_" << i 
                    << ",n_visited_" << i
                    << ",duration_" << i;
    }
    output_file << std::endl;

    output_file.close();
}

void dev_main() {
    // Job* j = new Job(3, 3, 2, std::vector<int>{2, 3});
    // Job* j2 = new Job(3, 3, 1, std::vector<int>{1, 1});
    // Job* j = new Job(5, 5, 2, std::vector<int>{1, 5});
    // Job* j2 = new Job(5, 5, 1, std::vector<int>{4, 4});

    // State* s = new State(std::vector<Job*>{j, j2});
    State* s = new State(std::vector<Job*>{
        new Job(11, 11, HI, std::vector<int>{2, 3}),
        new Job(12, 12, LO, std::vector<int>{6, 6}),
        new Job(3, 3, HI, std::vector<int>{1, 2}),
    });

    std::vector<std::function<bool(State*)>> safe_oracles, unsafe_oracles;

    safe_oracles = {&SafeOracle::all_idle_hi};
    unsafe_oracles = {&UnsafeOracle::hi_over_demand};

    Graph g(s, &Scheduler::lwlf, "./test.dot", 3, safe_oracles, unsafe_oracles);
    g.search({SearchAlgorithm::ACBFS});
}

int main(int argc, char** argv) {
    if (argc == 1) {
        dev_main();
    } else if (argc >= 4) {
        std::string xp_type = argv[1];
        std::string input_path = argv[2];
        std::string output_path = argv[3];
        std::function<void(State*, int, std::string)> experiment;
        int offset = 0;
        int n_experiments = -1;
        if (argc >= 5) offset = std::atoi(argv[4]);
        if (argc >= 6) n_experiments = std::atoi(argv[5]);

        if (xp_type == "antichain") {
            experiment = statespace_antichain_experiment;
        } else if (xp_type == "scheduling") {
            experiment = scheduling_performance_experiment;
        } else if (xp_type == "oracle") {
            experiment = statespace_oracle_experiment;
        } else if (xp_type == "antichain_oracle") {
            experiment = statespace_antichain_oracle_experiment;
        } else {
            std::cout << "Unknown experiment type: " << xp_type << std::endl;
            return 0;
        }

        const size_t max_algorithms = 2;
        output_file_setup(output_path, max_algorithms);
        read_task_sets(input_path, output_path, experiment, offset, n_experiments);
    } else {
        std::cout << "Usage: " << argv[0] << " <xp_type> <input_path> <output_path>" << std::endl;
        return 0;
    }

    return 0;
}
