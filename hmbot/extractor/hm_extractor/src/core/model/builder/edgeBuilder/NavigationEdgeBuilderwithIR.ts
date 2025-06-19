import { Stmt, ArkMethod, Scene, ArkAssignStmt, ArkInvokeStmt, Cfg, Local } from "../../../../arkanalyzer/src";
import { PageTransitionGraph, PTGNode } from "../../PageTransitionGraph";
import { StringConstant } from "../../../../arkanalyzer/src/core/base/Constant";
import Const from "../../../common/Constant";
import Utils, { MyValue } from "../../../common/Utils";
import { EdgeBuilderInterface } from "./EdgeBuilderInterface";


export class NavigationEdgeBuilderwithIR implements EdgeBuilderInterface{
    edgeBuilderStrategy: string = "NavigationEdgeBuilderwithIR";
    scene: Scene;
    ptg:PageTransitionGraph;

    constructor(scene: Scene, ptg: PageTransitionGraph){
        this.scene = scene;
        this.ptg = ptg;
    }

    identifyPTGEdge(ptgNode: PTGNode, method: ArkMethod): void {
        const cfg = method.getBody()?.getCfg();
        for(const unit of method.getCfg()!.getStmts()) {
            this.identifyPTGEdgeByIRAnalysis(ptgNode, unit, cfg!,  method);
        }
    }

    /**
     * 根据page迁移语句识别PTGEdge
     * 通过字节码分析
     * @param ptgNode 
     * @param unit 
     * @param cfg 
     * @param method 
     */
    identifyPTGEdgeByIRAnalysis(ptgNode: PTGNode, unit: Stmt, cfg: Cfg, method: ArkMethod) {
        // console.log("identify PTG edge by IR analysis");
        // 获取ptgNode所属的类名
        const caller = ptgNode.getClassOfPage().toString();
        let callee = "";
        // 判断unit是否为ArkInvokeStmt类型
        if(unit instanceof ArkInvokeStmt) {
            let expr = unit.getInvokeExpr();
            let invokeMethod = expr.getMethodSignature();
            const invokeMethodName = invokeMethod.getMethodSubSignature().getMethodName();
            // 判断调用表达式的方法名是否为pushUrl或replaceUrl
            for( let entry of Const.NAVITRANSTIONSTMTS.entries()){
                if(entry[0] == invokeMethodName){
                    // 获取cfg的def-use链
                    cfg?.buildDefUseChain(); 
                    const chains = cfg?.getDefUseChains();

                    // 获取 pageTargetVar的对象（匿名类）名称
                    let pageTargetVarLoction = entry[1];
                    let pageTargetValue = expr.getArg(pageTargetVarLoction); 
                    let targetPageName = "";
                    if(pageTargetValue != undefined){
                        //for local variable, get its concrete value first
                        if(pageTargetValue instanceof Local){
                            pageTargetValue = Utils.getValueOfVar(method, pageTargetValue, new MyValue())?.value
                        }
                        //获取目标页面类的名字
                        if(pageTargetValue instanceof StringConstant){
                            targetPageName  = (pageTargetValue as StringConstant).getValue();
                        }
                    }
                    for(let ptgNode of this.ptg.getPTGNodes()){
                        if(ptgNode.getPageAlias() == targetPageName){
                            callee = Utils.getComponentClassOfPage(this.scene, ptgNode.getPageName())!.getSignature().toString();
                            
                        }
                    }
                
                    
                    this.ptg.addPTGEdgeByName(caller, callee, unit);
                
                }

            }
        }
    }
    
}