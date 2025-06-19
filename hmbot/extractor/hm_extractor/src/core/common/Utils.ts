import { ArkAssignStmt, ArkClass, ArkMethod, FileSignature, Local, Scene, Value } from "../../arkanalyzer/src";

export default class Utils {
    
    static getValueOfClassFiled(scene: Scene, className: string, filedName: string): Local | undefined {
        let value = undefined;
        scene.getClasses().forEach((clazz: ArkClass) => {
            //find the inner class by name
            if(clazz.getSignature().toString() == className){
                for(const filed of clazz.getFields()){
                    if(filed.getName() == filedName){
                        for(let stmt of filed.getInitializer()){
                            if(stmt instanceof ArkAssignStmt){
                                value = stmt.getRightOp();
                                return value;
                            }
                        } 
                        
                    }
                }
            }
        });
        return value;
    }


    /**
     * 获取方法内给定变量的值
     * @param method 
     * @param targetVar 
     * @param targetValue 
     * @returns 
     */
    static getValueOfVar(method:ArkMethod, targetVar:Local, targetValue:MyValue){
        if(targetValue.historyVals.includes(targetVar)){
            return targetValue;
        }
        targetValue.historyVals.push(targetVar);
        const cfg = method.getBody()?.getCfg();
        for(let unit of cfg?.getStmts()!){
            if(unit instanceof ArkAssignStmt){
                let assignStmt = unit as ArkAssignStmt;
                if(assignStmt.getLeftOp().toString() == targetVar.toString()){
                    if (assignStmt.getRightOp()  instanceof Local){
                        this.getValueOfVar(method, assignStmt.getRightOp() as Local, targetValue);
                    }else{
                        targetValue.value = assignStmt.getRightOp();
                        targetValue.isFinish = true;
                        return targetValue;
                    }
                }
            }
        }
    }

    static getComponentClassOfPage(scene: Scene, page: string): ArkClass | undefined {
        const signature = new FileSignature(scene.getProjectName(), `entry/src/main/ets/${page}.ets`);
        const file = scene.getFile(signature);
        const classes = file?.getClasses();
        if(classes != undefined){
            for(const clazz of classes){
                if (clazz.hasComponentDecorator()) { //clazz.hasEntryDecorator() && 
                    return clazz;
                }
            }
        }
    }
}

export class MyValue{
    historyVals:Value[] = [];
    value:any;
    isFinish: boolean = false;
}
