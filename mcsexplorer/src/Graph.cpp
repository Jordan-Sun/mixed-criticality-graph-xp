#include "Graph.h"
#include "util.cpp"
#include <stack>

Graph::Graph() = default;

Graph::~Graph() { delete initial_state; }

bool Graph::is_fail(std::vector<State*> const& states) {
    for (State* state : states) {
        if (state->is_fail()) {
            log_fail(state);
            return true;
        }
    }
    return false;
}

void Graph::run_tansition(State* state, int to_run) { state->run_tansition(to_run); }

std::vector<State*> Graph::completion_transition(State* state, int to_run) {
    State* state_signals = new State(*state);
    state->completion_transition(to_run, false);
    state_signals->completion_transition(to_run, true);
    if (state->get_hash() != state_signals->get_hash()) {
        return std::vector<State*>{state, state_signals};
    }
    delete state_signals;
    return std::vector<State*>{state};
}

std::vector<State*> Graph::request_transition(State* state) {
    std::vector<State*> new_states;

    std::vector<size_t> eligibles_candidates = state->get_eligibles();
    std::vector<std::vector<int>> all_eligibles = power_set(eligibles_candidates);

    for (std::vector<int> const& current_eligibles : all_eligibles) {
        State* request_state = new State(*state);
        request_state->request_transition(current_eligibles);
        new_states.push_back(request_state);
    }

    delete state;

    return new_states;
}

std::vector<State*> Graph::request_periodic_transition(State* state) {
    std::vector<State*> new_states;

    std::vector<size_t> eligibles_candidates = state->get_eligibles();
    std::vector<int> eligibles_candidates_int =
        std::vector<int>(eligibles_candidates.begin(), eligibles_candidates.end());
    State* request_state = new State(*state);
    request_state->request_transition(eligibles_candidates_int);
    new_states.push_back(request_state);

    delete state;

    return new_states;
}

bool Graph::has_unsafe(std::vector<State*> const& states) {
    for (std::function<bool(State*)> unsafe_oracle : unsafe_oracles) {
        for (State* current_state : states) {
            if (unsafe_oracle(current_state)) {
                log_unsafe(current_state);
                return true;
            }
        }
    }
    return false;
}

void Graph::handle_safe(std::vector<State*>& states) {
    for (std::function<bool(State*)> safe_oracle : safe_oracles) {
        if (verbose >= 2) {
            for (State* current_state : states) {
                if (safe_oracle(current_state)) {
                    log_safe(current_state);
                }
            }
        }

        states.erase(std::remove_if(states.begin(), states.end(), safe_oracle), states.end());
    }
}

void Graph::handle_run_transition(std::vector<State*> const& states, std::vector<int> to_runs, bool is_last_leaf) {
    for (size_t i = 0; i < states.size(); ++i) {
        State* state = states[i];
        int to_run = to_runs[i];

        run_tansition(state, to_run);
        log_run(state, is_last_leaf);
    }
}

std::vector<State*> Graph::handle_completion_transition(std::vector<State*> const& states, std::vector<int> to_runs,
                                                        bool is_last_leaf) {
    std::vector<State*> all_completion_states = std::vector<State*>{};

    for (size_t i = 0; i < states.size(); ++i) {
        State* state = states[i];
        int to_run = to_runs[i];

        if (to_run > -1) {
            std::vector<State*> completion_states = completion_transition(state, to_run);

            for (State* new_state : completion_states) {
                all_completion_states.push_back(new_state);
            }
        } else {
            all_completion_states.push_back(state);
        }
    }

    for (size_t j = 0; j < all_completion_states.size(); ++j) {
        log_completion(all_completion_states[j], is_last_leaf, j == all_completion_states.size() - 1);
    }

    return all_completion_states;
}

std::vector<State*> Graph::handle_request_transition(State* state, bool is_last_leaf, bool periodic_only) {
    std::vector<State*> request_states;
    if (periodic_only) {
        request_states = request_periodic_transition(state);
    } else {
        request_states = request_transition(state);
    }

    for (size_t i = 0; i < request_states.size(); ++i) {
        State* request_state = request_states[i];
        log_request(request_state, is_last_leaf);
    }

    return request_states;
}

std::vector<State*> Graph::get_neighbors(std::vector<State*> const& leaf_states, bool periodic_only) {
    std::vector<State*> new_states;

    for (size_t leaf_i = 0; leaf_i < leaf_states.size(); ++leaf_i) {
        State* current_state = leaf_states[leaf_i];
        State* original_leaf_state = new State(*current_state);

        // verbose setup
        bool is_last_leaf = leaf_i == leaf_states.size() - 1;
        log_start(current_state, is_last_leaf);

        // apply all three transitions
        std::vector<State*> request_states = handle_request_transition(current_state, is_last_leaf, periodic_only);

        std::vector<int> to_runs = std::vector<int>{};
        for (State* request_state : request_states) {
            to_runs.push_back(schedule(request_state));
        }

        handle_run_transition(request_states, to_runs, is_last_leaf);
        std::vector<State*> neighbors = handle_completion_transition(request_states, to_runs, is_last_leaf);

        connect_neighbors_graphviz(original_leaf_state, neighbors);

        delete original_leaf_state;

        // add new states
        new_states.insert(new_states.end(), neighbors.begin(), neighbors.end());
    }

    return new_states;
}

void Graph::initialize_search(SearchAlgorithm algorithm) {
    automaton_is_safe = true;
    search_algorithm = algorithm;
    visited_count = 0;
    automaton_depth = 0;

    log_start_search();
    graphiz_setup();

    start = std::chrono::high_resolution_clock::now();
}

void Graph::finalize_search(Result& result) {
    auto stop = std::chrono::high_resolution_clock::now();
    duration = std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start);

    graphiz_teardown();
    log_end_search();

    result.is_safe = int64_t(automaton_is_safe);
    result.depth = automaton_depth;
    result.visited_count = visited_count;
    result.duration_ns = duration.count();
}

std::vector<Result> Graph::search(std::vector<SearchAlgorithm> algorithms) {
    // First perform the pilot heuristic search if specified
    std::vector<Result> results;

    // Perform the pilot heuristics in sequence, or none at all if empty.
    for (SearchAlgorithm algorithm : algorithms) {
        Result result;
        switch (algorithm) {
            case SearchAlgorithm::BFS:
            case SearchAlgorithm::PBFS:
                _bfs(result, algorithm == SearchAlgorithm::PBFS);
                break;
            case SearchAlgorithm::ACBFS:
            case SearchAlgorithm::PACBFS:
                _acbfs(result, algorithm == SearchAlgorithm::PACBFS);
                break;
            case SearchAlgorithm::DFS:
            case SearchAlgorithm::PDFS:
                _dfs(result, algorithm == SearchAlgorithm::PDFS);
                break;
            default:
                _dummy(result);
        }
        results.push_back(result);

        // if pilot heuristic already determines the automaton to be unsafe, return immediately without continuing.
        if (!result.is_safe) {
            return results;
        }
    }

    return results;
}

void Graph::_bfs(Result& result, bool periodic_only) {
    initialize_search(periodic_only ? SearchAlgorithm::PBFS : SearchAlgorithm::BFS);

    std::vector<State*> leaf_states{new State(*initial_state)};
    std::vector<State*> neighbors;

    std::unordered_set<uint64_t> visited_hashes;
    visited_hashes.insert(leaf_states[0]->get_hash());

    while (!leaf_states.empty()) {
        visited_count = visited_count + leaf_states.size();

        log_step(leaf_states.size());

        automaton_is_safe = not(is_fail(leaf_states) or has_unsafe(leaf_states));
        if (not automaton_is_safe) break;

        handle_safe(leaf_states);

        neighbors = get_neighbors(leaf_states, periodic_only);

        automaton_depth++;
        leaf_states.clear();

        for (State* neighbor : neighbors) {
            uint64_t neighbor_hash = neighbor->get_hash();
            if (visited_hashes.find(neighbor_hash) == visited_hashes.end()) {
                // the state has not been explored yet
                visited_hashes.insert(neighbor_hash);
                leaf_states.push_back(neighbor);
            } else {
                delete neighbor;
            }
        }
    }

    finalize_search(result);

    // not empty if automaton is unsafe
    for (State* unexplored_state : leaf_states) delete unexplored_state;
}

bool pairwise_smaller_all(std::vector<int> a, std::vector<int> b) {
    if (a.size() != b.size()) {
        // if this happens there is a bug in the code about antichain max set
        std::cout << "a" << std::endl;
        for (int i : a) {
            std::cout << i << std::endl;
        }
        std::cout << "b" << std::endl;
        for (int i : b) {
            std::cout << i << std::endl;
        }
    }
    for (unsigned int i = 0; i < a.size(); i++) {
        if (a[i] > b[i]) return false;
    }
    return true;
}

void Graph::_acbfs(Result& result, bool periodic_only) {
    initialize_search(periodic_only ? SearchAlgorithm::PACBFS : SearchAlgorithm::ACBFS);

    std::vector<State*> leaf_states{new State(*initial_state)};
    std::vector<State*> neighbors;

    std::unordered_map<uint64_t, std::unordered_map<uint64_t, std::vector<int>>> visited_hashes;

    uint64_t initial_state_hash = initial_state->get_hash_idle();
    uint64_t initial_state_idle_nats_hash;
    std::vector<int> initial_state_idle_nats_vector;
    std::tie(initial_state_idle_nats_hash, initial_state_idle_nats_vector) = initial_state->get_idle_nats_pair();

    visited_hashes[initial_state_hash][initial_state_idle_nats_hash] = initial_state_idle_nats_vector;

    while (!leaf_states.empty()) {
        visited_count = visited_count + leaf_states.size();

        log_step(leaf_states.size());

        automaton_is_safe = not(is_fail(leaf_states) or has_unsafe(leaf_states));
        if (not automaton_is_safe) break;

        handle_safe(leaf_states);

        neighbors = get_neighbors(leaf_states, periodic_only);

        automaton_depth++;
        leaf_states.clear();

        for (State* neighbor : neighbors) {
            uint64_t neighbor_hash = neighbor->get_hash_idle();

            uint64_t neighbor_idle_nats_hash;
            std::vector<int> neighbor_idle_nats_vector;
            std::tie(neighbor_idle_nats_hash, neighbor_idle_nats_vector) = neighbor->get_idle_nats_pair();

            if (visited_hashes.find(neighbor_hash) == visited_hashes.end()) {
                // this arrangement of active jobs and their respecting rct has
                // not been visited earlier so no visited state can simulate the
                // neighbor

                visited_hashes[neighbor_hash] = std::unordered_map<uint64_t, std::vector<int>>(
                    {{neighbor_idle_nats_hash, neighbor_idle_nats_vector}});
                leaf_states.push_back(neighbor);

            } else {
                // this arrangement of active jobs and their respecting rct has
                // been visited earlier and wether this neighbor is simulated or
                // not depends on the value of its nats
                bool neighbor_is_simulated = false;
                std::vector<u_int64_t> visited_is_simulated_hashes;

                if (visited_hashes[neighbor_hash].find(neighbor_idle_nats_hash) !=
                    visited_hashes[neighbor_hash].end()) {
                    // this exact state has already been visited and we do not
                    // need to explore it

                    log_visited(neighbor);

                    delete neighbor;
                } else {
                    for (const auto& [visited_idle_nat_hash, visited_idle_nat_vector] : visited_hashes[neighbor_hash]) {
                        if (pairwise_smaller_all(visited_idle_nat_vector, neighbor_idle_nats_vector)) {
                            neighbor_is_simulated = true;
                            simulate_neighbor_graphviz(neighbor, visited_idle_nat_vector);
                            break;
                        }
                        if (pairwise_smaller_all(neighbor_idle_nats_vector, visited_idle_nat_vector)) {
                            // this neighbor simulates some previously visited
                            // states which can safely be removed from memory
                            visited_is_simulated_hashes.push_back(visited_idle_nat_hash);
                        }
                    }
                    for (u_int64_t const& key : visited_is_simulated_hashes) {
                        visited_hashes[neighbor_hash].erase(key);
                    }
                    if (!neighbor_is_simulated) {
                        visited_hashes[neighbor_hash][neighbor_idle_nats_hash] = neighbor_idle_nats_vector;
                        leaf_states.push_back(neighbor);
                    } else {
                        log_simulated(neighbor);
                        delete neighbor;
                    }
                }
            }
        }
    }

    finalize_search(result);

    // not empty if automaton is unsafe
    for (State* unexplored_state : leaf_states) delete unexplored_state;
}

typedef struct {
    int from_depth;
    uint64_t from_hash;
    State* to;
} DFSEdge;

void Graph::_dfs(Result& result, bool periodic_only) {
    initialize_search(periodic_only ? SearchAlgorithm::PDFS : SearchAlgorithm::DFS);

    // Records from and current state so the graph can be drawn.
    std::stack<DFSEdge> unexplored_states;
    unexplored_states.push(DFSEdge{0, 0, new State(*initial_state)});
    std::vector<State*> neighbors;

    // std::unordered_set<uint64_t> visited_hashes;
    std::unordered_map<uint64_t, State*> visited_hash_states;

    while (!unexplored_states.empty()) {

        auto[from_depth, from_hash, current_state] = unexplored_states.top();
        unexplored_states.pop();
        from_depth++;

        uint64_t current_state_hash = current_state->get_hash();
        if (visited_hash_states.find(current_state_hash) != visited_hash_states.end()) {
            log_visited(current_state);
            delete current_state;
            continue;
        }
        // the state has not been explored yet
        visited_count++;
        if (from_hash != 0) connect_neighbor_graphviz(visited_hash_states[from_hash], current_state);
        visited_hash_states[current_state_hash] = new State(*current_state);
        automaton_depth = std::max(automaton_depth, from_depth);

        if (current_state->is_fail()) {
            log_fail(current_state);
            break;
        }

        // for (std::function<bool(State*)> unsafe_oracle : unsafe_oracles) {
        //     if (unsafe_oracle(current_state)) {
        //         log_unsafe(current_state);
        //         break;
        //     }
        // }

        // for (std::function<bool(State*)> safe_oracle : safe_oracles) {
        //     if (safe_oracle(current_state)) {
        //         log_safe(current_state);
        //         continue;
        //     }
        // }

        // apply all three transitions
        std::vector<State*> request_states;
        request_states = handle_request_transition(current_state, true, periodic_only);

        std::vector<int> to_runs = std::vector<int>{};
        for (State* request_state : request_states) {
            to_runs.push_back(schedule(request_state));
        }

        handle_run_transition(request_states, to_runs, true);
        std::vector<State*> neighbors = handle_completion_transition(request_states, to_runs, true);

        for (State* neighbor : neighbors) {
            uint64_t neighbor_hash = neighbor->get_hash();
            if (visited_hash_states.find(neighbor_hash) == visited_hash_states.end()) {
                unexplored_states.push(DFSEdge{from_depth, current_state_hash, neighbor});
            } else {
                delete neighbor;
            }
        }
    }

    finalize_search(result);

    // not empty if automaton is unsafe
    while (!unexplored_states.empty()) {
        auto[from_depth, from_hash, unexplored_state] = unexplored_states.top();
        unexplored_states.pop();
        delete unexplored_state;
    }
    for (const auto& [visited_hash, visited_state] : visited_hash_states) {
        delete visited_state;
    }
}

// GRAPHIZ FUNCTIONS

void Graph::graphiz_setup() {
    if (!plot_graph) {
        return;
    }

    std::ofstream o_file;
    o_file.open(graph_output_path);
    o_file << "digraph G "
              "{\n"
              "node[shape=\"box\",style=\"rounded,filled\", "
              "fontname=\"helvetica\"]"
              "\n";

    // initial_state
    o_file << "tasks_info [ shape=\"plaintext\",style=\"\",label = <\n"
              " <table bgcolor=\"black\" color=\"white\">\n"
              "  <tr>\n"
              "    <td bgcolor=\"white\">i</td>\n"
              "    <td bgcolor=\"white\">T</td>\n"
              "    <td bgcolor=\"white\">D</td>\n"
              "    <td bgcolor=\"white\">X</td>\n"
              "    <td bgcolor=\"white\">C1</td>\n"
              "    <td bgcolor=\"white\">C2</td>\n"
              "  </tr>\n";

    for (int i = 0; i < initial_state->get_size(); ++i) {
        Job* j = initial_state->get_job(i);
        o_file << "  <tr>\n";
        o_file << "    <td bgcolor=\"white\">" << i << "</td>\n";
        o_file << "    <td bgcolor=\"white\">" << j->get_T() << "</td>\n";
        o_file << "    <td bgcolor=\"white\">" << j->get_D() << "</td>\n";
        o_file << "    <td bgcolor=\"white\">" << j->get_X() << "</td>\n";
        o_file << "    <td bgcolor=\"white\">" << j->get_C()[0] << "</td>\n";
        o_file << "    <td bgcolor=\"white\">" << j->get_C()[1] << "</td>\n";
        o_file << "  </tr>\n";
    }
    o_file << " </table>\n"
              "> ]\n\n";

    o_file.close();

    std::stringstream legend;
    legend << "legend_nat_rct " << "[label=<rct,nat>,fillcolor=white]" << std::endl;
    legend << "legend_lo " << "[label=<LO>,fillcolor=lightcyan]" << std::endl;
    legend << "legend_hi " << "[label=<HI>,fillcolor=lightyellow]" << std::endl;
    legend << "legend_fail " << "[label=<fail>,color=orchid,fillcolor=white,penwidth=5]" << std::endl;
    legend << "legend_simulated " << "[label=<simulated>,color=blue,fillcolor=white,penwidth=5]" << std::endl;
    legend << "legend_safe " << "[label=<safe>,color=green,fillcolor=white,penwidth=5]" << std::endl;
    legend << "legend_unsafe " << "[label=<unsafe>,color=red,fillcolor=white,penwidth=5]" << std::endl;
    append_to_file(graph_output_path, legend.str());
}

void Graph::graphiz_teardown() {
    if (!plot_graph) {
        return;
    }
    append_to_file(graph_output_path, "\n}");
}

void Graph::connect_neighbor_graphviz(State* from, State* to) const {
    if (!plot_graph) {
        return;
    }

    std::string from_node_id;
    std::string to_node_id;
    if (not uses_idle_antichain(search_algorithm)) {
        from_node_id = from->get_node_id();
        to_node_id = to->get_node_id();
    } else {
        from_node_id = from->get_node_idle_id();
        to_node_id = to->get_node_idle_id();
    }

    std::string to_node_arg = "";
    if (!to->is_fail()) {
        for (std::function<bool(State*)> safe_oracle : safe_oracles) {
            if (safe_oracle(to)) {
                to_node_arg = ",color=green,penwidth=5";
                break;
            }
        }
        for (std::function<bool(State*)> unsafe_oracle : unsafe_oracles) {
            if (unsafe_oracle(to)) {
                to_node_arg = ",color=red,penwidth=5";
                break;
            }
        }
    }

    std::string from_node_desc = from->dot_node(from_node_id);
    std::string to_node_desc = to->dot_node(to_node_id, to_node_arg);

    std::stringstream edge_desc;

    edge_desc << from_node_id << " -> " << to_node_id << std::endl;

    append_to_file(graph_output_path, from_node_desc);
    append_to_file(graph_output_path, to_node_desc);
    append_to_file(graph_output_path, edge_desc.str());
};

void Graph::connect_neighbors_graphviz(State* from, std::vector<State*> to_list) const {
    if (!plot_graph) {
        return;
    }
    for (State* to : to_list) {
        connect_neighbor_graphviz(from, to);
    }
}

void Graph::simulate_neighbor_graphviz(State* neighbor, std::vector<int> nats) const {
    std::stringstream simulator_hash;
    simulator_hash << "n_";
    simulator_hash << neighbor->get_hash_idle();
    for (int nat : nats) {
        simulator_hash << "_" << nat;
    }

    std::stringstream set_simulated_state_border;
    set_simulated_state_border << neighbor->get_node_idle_id() << " [color=blue,penwidth=5]" << std::endl;
    append_to_file(graph_output_path, set_simulated_state_border.str());

    std::stringstream connect_simulated_state;
    connect_simulated_state << neighbor->get_node_idle_id() << " -> " << simulator_hash.str() << " [style=\"dashed\"]"
                            << std::endl;
    // append_to_file(graph_output_path, connect_simulated_state.str());
}

// LOGGING FUNCTIONS

void Graph::repr(std::vector<State*> states) {
    for (size_t i = 0; i < states.size(); ++i) {
        std::cout << "S" << i << "-> " << states[i]->str() << std::endl;
    }
    std::cout << std::endl;
}

void Graph::log_start_search() {
    if (verbose >= 0)
        std::cout << "┌██ Start " << get_full_name(search_algorithm) << std::endl;
}

void Graph::log_end_search() {
    if (verbose >= 0)
        std::cout << "└██ Automaton is " << (automaton_is_safe ? "SAFE" : "UNSAFE") << " | visited " << visited_count
                  << " states | depth " << automaton_depth << " | time " << duration.count() << " ms" << std::endl;
}

void Graph::log_step(int leaf_states_size) {
    if (verbose >= 1)
        std::cout << "├" << (verbose >= 2 ? "┬" : "") << " Depth: " << automaton_depth << ", visited: " << visited_count
                  << ", leaf state size: " << leaf_states_size << std::endl;
}

void Graph::log_fail(State* fail_state) {
    if (verbose >= 2) {
        std::cout << "│└ FAIL  " << fail_state->str() << std::endl;
    }
}

void Graph::log_unsafe(State* unsafe_state) {
    if (verbose >= 2) {
        std::cout << "│└ UNSAFE  " << unsafe_state->str() << std::endl;
    }
}

void Graph::log_safe(State* safe_state) {
    if (verbose >= 2) {
        std::cout << "│├ SAFE  " << safe_state->str() << std::endl;
    }
}

std::string Graph::get_second_hiearchy_char(bool is_last_leaf) {
    return is_last_leaf ? std::string(" ") : std::string("│");
}

std::string Graph::get_third_hiearchy_char(bool is_last_request) {
    return is_last_request ? std::string("└") : std::string("├");
}

void Graph::log_start(State* state, bool is_last_leaf) {
    std::string second_hiearchy_char = is_last_leaf ? std::string("└") : std::string("├");
    if (verbose >= 2) {
        std::cout << "│" << second_hiearchy_char << "┬ ";
        std::cout << "START " << state->str() << std::endl;
    }
}

void Graph::log_run(State* state, bool is_last_leaf) {
    if (verbose >= 2) {
        std::cout << "│" << get_second_hiearchy_char(is_last_leaf) << "├ ";
        std::cout << "RUN " << state->str() << std::endl;
    }
}

void Graph::log_completion(State* state, bool is_last_leaf, bool is_last_state) {
    if (verbose >= 2) {
        std::cout << "│" << get_second_hiearchy_char(is_last_leaf) << get_third_hiearchy_char(is_last_state) << " ";
        std::cout << "COMPLETION " << state->str() << std::endl;
    }
}

void Graph::log_request(State* state, bool is_last_leaf) {
    if (verbose >= 2) {
        std::cout << "│" << get_second_hiearchy_char(is_last_leaf) << "├ ";
        std::cout << "REQUEST " << state->str() << std::endl;
    }
}

void Graph::log_simulated(State* simulated_state) {
    if (verbose >= 2) {
        std::cout << "├ SIMULATED " << simulated_state->str() << std::endl;
    }
}

void Graph::log_visited(State* visited_state) {
    if (verbose >= 3) {
        std::cout << "├ ALREADY VISITED " << visited_state->str() << std::endl;
    }
}
