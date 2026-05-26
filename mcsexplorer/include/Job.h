#ifndef JOB_H
#define JOB_H

#include "Types.h"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#pragma once

class Job {
   public:
    Job() = default;

    Job(int T, int D, Criticality X, std::vector<int> const& C, int C_s, int p = 0)
        : T(T), D(D), X(X), C_s(C_s), C(std::move(C)), p(p) {
        initialize();
    };

    explicit Job(Job* other)
        : T(other->T),
          D(other->D),
          X(other->X),
          C_s(other->C_s),
          C(other->C),
          p(other->p),
          rst(other->rst),
          rct(other->rct),
          nat(other->nat),
          utilisation(other->utilisation){};
    Job(Job const& other) = default;
    ~Job() = default;

    int get_T() const { return T; };
    int get_D() const { return D; };
    int get_X() const { return X; };
    // TODO we use L_i in the paper; maybe we change that to avoid confusion?
    int get_C_s() const { return C_s; };
    std::vector<int> get_C() const { return C; };
    int get_C(Criticality criticality) const { return C[criticality - 1]; };
    int get_p() const { return p; };

    int get_rst() const { return rst; };
    int get_rct() const { return rct; };
    int get_nat() const { return nat; };

    int get_ttd() const { return nat - (T - D); };
    float get_ttvd(float discount_factor) const;
    float get_ttsd(float discount_factor) const;
    int get_laxity() const { return get_ttd() - rct; };
    int get_worst_laxity(Criticality current_crit) const { return get_ttd() - rct - (C[1] - C[current_crit - 1]); };

    bool is_unchecked() const { return rst > 0; };
    bool is_active() const { return rct > 0; };
    bool is_eligible(int crit) const { return rct == 0 and nat == 0 and X >= crit; };
    bool is_implicitly_completed(int crit) const { return rct == 0 and C[crit - 1] == C[X - 1]; };
    bool is_deadline_miss() const { return rct > 0 and get_ttd() <= 0; };
    bool is_discarded(int crit) const { return X < crit; };

    // execute the job for a tick with run indicating whether the job was chosen to run or not
    void execute(bool run);
    // terminate the job
    void terminate();
    // release the job under criticality crit
    void request(int crit);
    void critic(int current_crit, int next_crit, bool is_triggering);

    float get_utilisation_at_level(int at_level) const { return utilisation[at_level - 1]; };

    std::string str() const;
    std::string str_task() const;
    std::string dot_node() const;
    void repr() const;

    uint64_t get_hash() const;
    uint64_t get_hash_factor() const;
    uint64_t get_hash_idle() const;

    int get_next_jobs(int t, Criticality alpha) const;
    int get_demand(int t, Criticality alpha, Criticality current_crit) const;

   private:
    int T;
    int D;
    Criticality X;
    int C_s; // switching time for quarter-clairvoyant
    std::vector<int> C;
    int p;  // priority for FJP/FTP

    int rst; // remaining switching time
    int rct;
    int nat;

    float u_s = float(C_s) / float(T); // switching utilization
    std::vector<float> utilisation =
        std::vector<float>{compute_utilisation_at_level(1), compute_utilisation_at_level(2)};

    float compute_utilisation_at_level(int at_level) const { return float(C[at_level - 1]) / float(T); }

    void initialize();
};

#endif
