import { Stmt, ArkMethod, FileSignature, Scene } from "../../../../arkanalyzer/src";
import { PageTransitionGraph, PTGNode } from "../../PageTransitionGraph";
import Const from "../../../common/Constant";
import fs from "fs";
import Utils from "../../../common/Utils";
import { NodeBuilderInterface } from "./NodeBuilderInterface";

export class MainPageNodeBuilder implements NodeBuilderInterface{
    nodeBuilderStrategy: string = "MainPageNodeBuilder";
    scene: Scene;
    ptg:PageTransitionGraph;

    constructor(scene: Scene, ptg: PageTransitionGraph){
        this.scene = scene;
        this.ptg = ptg;
    }

    public identifyPageNodes(){
        const mainPagesFile =this.scene.getRealProjectDir() +Const.MAINPAGEFILES;
        const mainPagesText = fs.readFileSync(mainPagesFile, 'utf-8');
        const pages = JSON.parse(mainPagesText).src;

        for(const page of pages) {
            let clazz = Utils.getComponentClassOfPage(this.scene, page);
            if(clazz != undefined){
                let viewTree = clazz?.getViewTree();
                // ptgNodes.push
                this.ptg.addPTGNode(page, clazz, viewTree);
            }
        }
    }

    
        
    
}