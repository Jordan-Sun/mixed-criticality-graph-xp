#include "Graph.h"
#include <list>

typedef struct DFSEdge_t {
    int from_depth;
    uint64_t from_hash;
    State* to;
} DFSEdge;

class UniqueStack {
   protected:
    std::list<DFSEdge> unexplored_states;
    std::unordered_map<uint64_t, std::list<DFSEdge>::iterator> queued_states;

   public:
    UniqueStack() = default;

    UniqueStack(const UniqueStack&) = delete;
    UniqueStack& operator=(const UniqueStack&) = delete;

    ~UniqueStack() { clear(); }

    bool empty() const { return unexplored_states.empty(); }

    void push(DFSEdge edge) {
        uint64_t to_hash = edge.to->get_hash();

        auto existing_edge = queued_states.find(to_hash);

        if (existing_edge == queued_states.end()) {
            // push on top of the stack
            unexplored_states.push_back(edge);
            queued_states.emplace(to_hash, std::prev(unexplored_states.end()));
        } else {
            // update the entry instead
            auto& edge_it = existing_edge->second;
            delete edge_it->to;
            *edge_it = edge;
            // move to top of the stack
            unexplored_states.splice(unexplored_states.end(), unexplored_states, edge_it);
        }
    }

    DFSEdge pop() {
        DFSEdge edge = unexplored_states.back();
        unexplored_states.pop_back();

        queued_states.erase(edge.to->get_hash());

        return edge;
    }

    void clear() {
        for (DFSEdge& edge : unexplored_states) {
            delete edge.to;
        }

        unexplored_states.clear();
        queued_states.clear();
    }
};