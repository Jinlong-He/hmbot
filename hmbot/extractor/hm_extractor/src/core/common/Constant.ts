export default class Const {
    static readonly BUILDCONFIG = "build-profile.json5";

    static readonly MAINPAGEFILES = "/entry/src/main/resources/base/profile/main_pages.json";
    static readonly ROUTERMAPFILE = "/entry/src/main/resources/base/profile/router_map.json";


    static ROUTERTRANSTIONSTMTS: Map<string, number> = new Map([
        ['pushUrl', 0],
        ['replaceUrl', 0]
    ]);
    static NAVITRANSTIONSTMTS: Map<string, number> = new Map([
        ['pushPathByName', 0],
        ['pushPath', 0]
    ]);
    static readonly PAGETARGETOBJNAME = "url";
}