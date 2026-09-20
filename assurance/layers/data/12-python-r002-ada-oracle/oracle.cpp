// Direct Ada 2.9.2 reference oracle harness (assurance/research tooling only).
// Mirrors Node v22.19.0's own src/node_url.cc call sequence exactly:
//   ada::parse<ada::url>(url) -> get_hostname() -> ada::idna::to_unicode(hostname)
// Reads one full "file://..." URL per line on stdin (UTF-8), writes
// "<url>\t<PARSE_ERROR|decoded-unicode-host>\n" per line to stdout (UTF-8).
#include "ada.h"
#include <iostream>
#include <string>

int main() {
    std::ios::sync_with_stdio(false);
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        auto url = ada::parse<ada::url>(line);
        if (!url) {
            std::cout << line << "\tPARSE_ERROR\n";
            continue;
        }
        std::string_view hostname = url->get_hostname();
        std::string decoded = ada::idna::to_unicode(hostname);
        std::cout << line << "\t" << decoded << "\n";
    }
    return 0;
}
