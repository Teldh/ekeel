import React from 'react';
import './Welcome.css'
import Header from '../Header/Header'
import {TokenContext} from './../account-management/TokenContext'
import tuto from '../../logo/tuto.png'
import {
    Link,
  } from "react-router-dom";
import LoginButton from '../Header/LoginButton'

{/*
    This is the welcome page of the application
    It shows the logo, the title and a tutorial at the bottom
*/}
export default class Welcome extends React.Component {

    static contextType = TokenContext;

    render() {
        return (
            <div style={{height: "auto"}}>
                <Header page="welcome" login={null}/>
                <div className="contentContainer">
                    <text className="welcomeTitle">
                        Welcome to EKEEL!
                    </text>
                    <text className="welcomeSubtitle">
                        EKEEL enhances your navigation and exploration of  concepts  explained in  video lessons.
                    </text> 
                    <text className="welcomeSubtitle">
                    First login and then try EKEEL services to improve your distance learning!
                    </text>
                    <Link className="link" style={{fontSize: 20}} to="/login"><LoginButton/></Link>
                </div>
                
                <div class="featureList">
                    
                    <text>
                    A quick view of some of the features available
                    </text>  
                    <text style={{marginTop: '10px'}}>
                    EKEEL enables you to:
                    <ul>
                    <li>see the explained concepts as a graph </li>
                    <li>search for specific concepts within the video</li>
                    <li>exploit the video fragment navigation</li>
                    </ul>  
                    </text>
                </div>

                <div className="tutoContainer">
                    <img className="tuto" src={tuto} alt="tuto"></img>
                </div>
            </div>
        )
    }
}